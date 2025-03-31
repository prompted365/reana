"""
Circuit Breaker pattern implementation for API calls

This module provides a circuit breaker implementation that can be used to prevent
cascading failures when making calls to external services.
"""

import time
import logging
import asyncio
from enum import Enum
from typing import Callable, Any, Dict, Optional, List, Type

from app.utils.monitoring import track_circuit_breaker

# Configure logging
logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Possible states for the circuit breaker"""
    CLOSED = "closed"  # Normal operation, requests are allowed
    OPEN = "open"      # Circuit is tripped, requests are blocked
    HALF_OPEN = "half_open"  # Testing if service has recovered


class CircuitBreakerOpenError(Exception):
    """Exception raised when a call is attempted with an open circuit breaker"""
    pass


class CircuitBreaker:
    """
    Implementation of the circuit breaker pattern
    
    The circuit breaker monitors calls to external services and trips
    when too many failures occur in a short time. This prevents overwhelming
    a failing service and allows for graceful degradation.
    """
    
    def __init__(self, 
                 name: str,
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 half_open_max_calls: int = 1,
                 excluded_exceptions: Optional[List[Type[Exception]]] = None):
        """
        Initialize the circuit breaker
        
        Args:
            name: Name of this circuit breaker (for logging and identification)
            failure_threshold: Number of failures before the circuit opens
            recovery_timeout: Seconds to wait before transitioning to half-open
            half_open_max_calls: Maximum number of calls allowed in half-open state
            excluded_exceptions: Exceptions that should not count as failures
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_calls = half_open_max_calls
        self.excluded_exceptions = excluded_exceptions or []
        
        # State tracking
        self._state = CircuitState.CLOSED
        self._failures = 0
        self._last_failure_time = 0
        self._successful_half_open_calls = 0
        self._half_open_calls_in_progress = 0
        
        # Lock for state changes
        self._state_lock = asyncio.Lock()
        
        logger.info(f"Circuit breaker '{name}' initialized with failure threshold {failure_threshold}")
        
    @property
    def state(self) -> CircuitState:
        """Get the current state of the circuit"""
        return self._state
        
    async def record_success(self):
        """Record a successful call and update monitoring"""
        async with self._state_lock:
            if self._state == CircuitState.HALF_OPEN:
                self._successful_half_open_calls += 1
                logger.info(f"Circuit breaker '{self.name}' recorded successful half-open call "
                          f"({self._successful_half_open_calls}/{self.half_open_max_calls})")
                
                # If we've had enough successes in half-open state, close the circuit
                if self._successful_half_open_calls >= self.half_open_max_calls:
                    logger.info(f"Circuit breaker '{self.name}' closing circuit after successful recovery")
                    self._state = CircuitState.CLOSED
                    self._failures = 0
                    self._successful_half_open_calls = 0
                    self._half_open_calls_in_progress = 0
                    
                    # Record state change in monitoring system
                    track_circuit_breaker(self.name, self._state.value, self._failures)
            
            # Always reset failures on success in closed state
            elif self._state == CircuitState.CLOSED:
                self._failures = 0
                track_circuit_breaker(self.name, self._state.value, self._failures)
                
    async def record_failure(self, exception: Exception = None):
        """Record a failed call and update monitoring"""
        """
        Record a failed call
        
        Args:
            exception: The exception that caused the failure
        """
        # Don't record failure if it's an excluded exception
        if exception and any(isinstance(exception, exc) for exc in self.excluded_exceptions):
            logger.debug(f"Circuit breaker '{self.name}' ignoring excluded exception: {str(exception)}")
            return
            
        async with self._state_lock:
            now = time.time()
            
            if self._state == CircuitState.CLOSED:
                self._failures += 1
                self._last_failure_time = now
                
                logger.warning(f"Circuit breaker '{self.name}' recorded failure "
                             f"({self._failures}/{self.failure_threshold})")
                
                # If we've hit the threshold, open the circuit
                if self._failures >= self.failure_threshold:
                    logger.warning(f"Circuit breaker '{self.name}' tripped after {self._failures} failures")
                    self._state = CircuitState.OPEN
                    
                    # Record state change in monitoring system
                    track_circuit_breaker(self.name, self._state.value, self._failures)
                    
            elif self._state == CircuitState.HALF_OPEN:
                logger.warning(f"Circuit breaker '{self.name}' failed in half-open state, reopening circuit")
                self._state = CircuitState.OPEN
                self._last_failure_time = now
                self._successful_half_open_calls = 0
                self._half_open_calls_in_progress = 0
                # Record state change in monitoring system
                track_circuit_breaker(self.name, self._state.value, self._failures)
                 
    async def allow_request(self) -> bool:
        """
        Check if a request should be allowed based on the current circuit state
        
        Returns:
            bool: True if the request is allowed, False otherwise
        """
        async with self._state_lock:
            now = time.time()
            
            if self._state == CircuitState.CLOSED:
                # Always allow in closed state
                return True
                
            elif self._state == CircuitState.OPEN:
                # Check if it's time to transition to half-open
                if now - self._last_failure_time >= self.recovery_timeout:
                    logger.info(f"Circuit breaker '{self.name}' transitioning to half-open state "
                              f"after {self.recovery_timeout}s timeout")
                    self._state = CircuitState.HALF_OPEN
                    self._successful_half_open_calls = 0
                    
                    # Record state change in monitoring system
                    track_circuit_breaker(self.name, self._state.value, self._failures)
                    
                    self._half_open_calls_in_progress = 0
                    return True
                else:
                    # Still open, don't allow
                    time_left = self.recovery_timeout - (now - self._last_failure_time)
                    logger.debug(f"Circuit breaker '{self.name}' is open, blocking request "
                               f"(retry after ~{int(time_left)}s)")
                    return False
                    
            elif self._state == CircuitState.HALF_OPEN:
                # Only allow limited calls in half-open state
                if self._half_open_calls_in_progress < self.half_open_max_calls:
                    self._half_open_calls_in_progress += 1
                    logger.info(f"Circuit breaker '{self.name}' allowing half-open test call "
                              f"({self._half_open_calls_in_progress}/{self.half_open_max_calls})")
                    return True
                else:
                    logger.debug(f"Circuit breaker '{self.name}' is half-open with max calls "
                               f"in progress, blocking request")
                    return False
                
            # Shouldn't get here, but just in case
            return True
            
    async def execute(self, func, *args, **kwargs):
        """
        Execute a function with circuit breaker protection
        
        Args:
            func: Async function to execute
            *args: Arguments to pass to the function
            **kwargs: Keyword arguments to pass to the function
            
        Returns:
            The result of the function call
            
        Raises:
            CircuitBreakerOpenError: If the circuit is open and the call is blocked
            Any exceptions raised by the function
        """
        if not await self.allow_request():
            raise CircuitBreakerOpenError(f"Circuit breaker '{self.name}' is open")
            
        try:
            result = await func(*args, **kwargs)
            await self.record_success()
            return result
        except Exception as e:
            await self.record_failure(e)
            raise