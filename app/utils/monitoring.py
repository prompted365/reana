"""
Monitoring utilities for tracking API usage, rate limits, and circuit breaker states.

This module provides classes and functions for:
1. Tracking API call statistics
2. Monitoring rate limit consumption
3. Tracking circuit breaker state changes
4. Logging performance metrics for API calls
"""

import time
import logging
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from enum import Enum
import threading

logger = logging.getLogger(__name__)

class MetricType(Enum):
    """Types of metrics that can be collected."""
    API_CALL = "api_call"
    RATE_LIMIT = "rate_limit"
    CIRCUIT_STATE = "circuit_state"
    RETRY_COUNT = "retry_count"
    TOKEN_REFRESH = "token_refresh"
    ERROR_COUNT = "error_count"
    RESPONSE_TIME = "response_time"


@dataclass
class ApiCallStats:
    """Statistics for API calls."""
    endpoint: str
    success_count: int = 0
    error_count: int = 0
    retry_count: int = 0
    total_response_time: float = 0.0
    response_times: List[float] = field(default_factory=list)
    rate_limit_hits: int = 0
    last_called: Optional[datetime] = None
    
    @property
    def total_count(self) -> int:
        """Total number of API calls."""
        return self.success_count + self.error_count
    
    @property
    def average_response_time(self) -> float:
        """Average response time in seconds."""
        if self.success_count == 0:
            return 0.0
        return self.total_response_time / self.success_count
    
    @property
    def percentile_95(self) -> float:
        """95th percentile response time."""
        if not self.response_times:
            return 0.0
        return statistics.quantiles(self.response_times, n=20)[-1]
    
    def add_response_time(self, response_time: float) -> None:
        """Add a response time measurement."""
        self.response_times.append(response_time)
        self.total_response_time += response_time
        
        # Keep only the most recent 1000 measurements to avoid memory issues
        if len(self.response_times) > 1000:
            removed_time = self.response_times.pop(0)
            self.total_response_time -= removed_time


@dataclass
class RateLimitStats:
    """Statistics for rate limiting."""
    endpoint: str
    limit: int = 0
    remaining: int = 0
    reset_time: Optional[datetime] = None
    last_updated: Optional[datetime] = None


@dataclass
class CircuitBreakerStats:
    """Statistics for circuit breaker states."""
    name: str
    current_state: str = "CLOSED"
    failure_count: int = 0
    state_change_count: int = 0
    last_state_change: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    last_success: Optional[datetime] = None
    open_duration: timedelta = field(default_factory=lambda: timedelta(0))
    total_open_time: timedelta = field(default_factory=lambda: timedelta(0))


class ApiMonitor:
    """
    Monitor for tracking API usage, rate limits, and circuit breaker states.
    
    This class provides methods for recording metrics and retrieving statistics
    about API usage and performance.
    """
    
    def __init__(self):
        self._api_stats: Dict[str, ApiCallStats] = {}
        self._rate_limits: Dict[str, RateLimitStats] = {}
        self._circuit_stats: Dict[str, CircuitBreakerStats] = {}
        self._lock = threading.RLock()
        
    def record_api_call(self, endpoint: str, success: bool, 
                       response_time: float, retries: int = 0) -> None:
        """
        Record statistics for an API call.
        
        Args:
            endpoint: The API endpoint called
            success: Whether the call was successful
            response_time: Response time in seconds
            retries: Number of retries performed
        """
        with self._lock:
            if endpoint not in self._api_stats:
                self._api_stats[endpoint] = ApiCallStats(endpoint=endpoint)
                
            stats = self._api_stats[endpoint]
            if success:
                stats.success_count += 1
                stats.add_response_time(response_time)
            else:
                stats.error_count += 1
                
            stats.retry_count += retries
            stats.last_called = datetime.now()
    
    def record_rate_limit(self, endpoint: str, limit: int, 
                         remaining: int, reset_time: datetime) -> None:
        """
        Record rate limit information for an endpoint.
        
        Args:
            endpoint: The API endpoint
            limit: The maximum number of requests allowed
            remaining: The number of requests remaining
            reset_time: When the rate limit will reset
        """
        with self._lock:
            if endpoint not in self._rate_limits:
                self._rate_limits[endpoint] = RateLimitStats(endpoint=endpoint)
                
            stats = self._rate_limits[endpoint]
            stats.limit = limit
            stats.remaining = remaining
            stats.reset_time = reset_time
            stats.last_updated = datetime.now()
            
            # Record if we hit the rate limit
            if remaining == 0 and endpoint in self._api_stats:
                self._api_stats[endpoint].rate_limit_hits += 1
    
    def record_circuit_state(self, name: str, state: str, 
                            failure_count: int) -> None:
        """
        Record circuit breaker state changes.
        
        Args:
            name: The name of the circuit breaker
            state: The current state (CLOSED, OPEN, HALF-OPEN)
            failure_count: The current failure count
        """
        with self._lock:
            now = datetime.now()
            
            if name not in self._circuit_stats:
                self._circuit_stats[name] = CircuitBreakerStats(name=name)
                
            stats = self._circuit_stats[name]
            old_state = stats.current_state
            
            # Update state and counts
            stats.failure_count = failure_count
            
            # Handle state changes
            if old_state != state:
                stats.state_change_count += 1
                stats.last_state_change = now
                
                # Calculate time spent in OPEN state
                if old_state == "OPEN" and stats.last_state_change:
                    open_duration = now - stats.last_state_change
                    stats.open_duration = open_duration
                    stats.total_open_time += open_duration
                    
            stats.current_state = state
            
            # Update failure/success timestamps
            if state == "OPEN" and old_state != "OPEN":
                stats.last_failure = now
            elif state == "CLOSED" and old_state != "CLOSED":
                stats.last_success = now
    
    def get_api_stats(self, endpoint: Optional[str] = None) -> Dict[str, ApiCallStats]:
        """
        Get API call statistics.
        
        Args:
            endpoint: Specific endpoint to get stats for, or None for all
            
        Returns:
            Dictionary of API call statistics
        """
        with self._lock:
            if endpoint:
                return {endpoint: self._api_stats.get(endpoint, 
                        ApiCallStats(endpoint=endpoint))}
            return self._api_stats.copy()
    
    def get_rate_limits(self, endpoint: Optional[str] = None) -> Dict[str, RateLimitStats]:
        """
        Get rate limit statistics.
        
        Args:
            endpoint: Specific endpoint to get stats for, or None for all
            
        Returns:
            Dictionary of rate limit statistics
        """
        with self._lock:
            if endpoint:
                return {endpoint: self._rate_limits.get(endpoint, 
                        RateLimitStats(endpoint=endpoint))}
            return self._rate_limits.copy()
    
    def get_circuit_stats(self, name: Optional[str] = None) -> Dict[str, CircuitBreakerStats]:
        """
        Get circuit breaker statistics.
        
        Args:
            name: Specific circuit breaker to get stats for, or None for all
            
        Returns:
            Dictionary of circuit breaker statistics
        """
        with self._lock:
            if name:
                return {name: self._circuit_stats.get(name, 
                        CircuitBreakerStats(name=name))}
            return self._circuit_stats.copy()

    def reset_stats(self) -> None:
        """Reset all statistics."""
        with self._lock:
            self._api_stats.clear()
            self._rate_limits.clear()
            self._circuit_stats.clear()


# Global monitor instance for application-wide use
api_monitor = ApiMonitor()


class ApiMetricsContext:
    """
    Context manager for automatically tracking API call metrics.
    
    Usage:
        with ApiMetricsContext("endpoint_name") as ctx:
            response = make_api_call()
            ctx.set_success(True)
            
            # Optionally track rate limits if available in response
            if 'rate_limit' in response:
                ctx.record_rate_limit(
                    response['rate_limit']['limit'],
                    response['rate_limit']['remaining'],
                    response['rate_limit']['reset']
                )
    """
    
    def __init__(self, endpoint: str):
        self.endpoint = endpoint
        self.start_time = None
        self.success = False
        self.retries = 0
        
    def __enter__(self):
        self.start_time = time.time()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is not None:
            response_time = time.time() - self.start_time
            api_monitor.record_api_call(
                self.endpoint, 
                self.success, 
                response_time, 
                self.retries
            )
        
    def set_success(self, success: bool) -> None:
        """Set whether the API call was successful."""
        self.success = success
        
    def set_retries(self, retries: int) -> None:
        """Set the number of retries performed."""
        self.retries = retries
        
    def record_rate_limit(self, limit: int, remaining: int, 
                        reset_time: datetime) -> None:
        """Record rate limit information."""
        api_monitor.record_rate_limit(
            self.endpoint, limit, remaining, reset_time
        )


# Module-level function for tracking circuit breaker state changes
def track_circuit_breaker(circuit_name: str, state: str, 
                         failure_count: int) -> None:
    """
    Track circuit breaker state changes.
    
    Args:
        circuit_name: Name of the circuit breaker
        state: Current state (CLOSED, OPEN, HALF-OPEN)
        failure_count: Current failure count
    """
    api_monitor.record_circuit_state(circuit_name, state, failure_count)