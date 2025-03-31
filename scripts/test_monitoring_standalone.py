#!/usr/bin/env python3
"""
Standalone test script for the monitoring system.

This version doesn't rely on application-specific imports that might
cause import errors. It directly tests the monitoring functionality.
"""

import sys
import os
import asyncio
import json
import random
import logging
from datetime import datetime, timedelta
import time
from pprint import pprint

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import only the monitoring module
from app.utils.monitoring import ApiMetricsContext, api_monitor, track_circuit_breaker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def simulate_api_call(endpoint, success=True, response_time=None, retries=0):
    """Simulate an API call and record metrics."""
    if response_time is None:
        # Generate a realistic response time between 50ms and 500ms
        response_time = random.uniform(0.05, 0.5)
    
    # Use context manager to track API metrics
    with ApiMetricsContext(endpoint) as metrics:
        # Simulate the API call by sleeping for the response time
        time.sleep(response_time)
        
        # Set success and retries in the metrics context
        metrics.set_success(success)
        metrics.set_retries(retries)
        
        # If this endpoint provides rate limit info, simulate that too
        if "rate-limited" in endpoint:
            # Simulate rate limit information
            limit = 100
            remaining = random.randint(5, 95)  # Random remaining requests
            reset_time = datetime.utcnow() + timedelta(minutes=1)  # Reset in 1 minute
            
            # Record rate limit information
            metrics.record_rate_limit(limit, remaining, reset_time)
    
    return {"success": success, "response_time": response_time}


def simulate_circuit_breaker_states():
    """Simulate circuit breaker state changes and track them."""
    logger.info("Simulating circuit breaker state changes...")
    
    # Simulate a circuit breaker going through state transitions
    circuit_names = ["api-circuit", "database-circuit", "external-service"]
    states = ["closed", "open", "half_open"]
    
    for circuit in circuit_names:
        # Start in closed state
        track_circuit_breaker(circuit, "closed", 0)
        logger.info(f"Circuit {circuit} starting in CLOSED state")
        
        # Simulate failures leading to open state
        for i in range(5):
            failure_count = i + 1
            track_circuit_breaker(circuit, "closed", failure_count)
            logger.info(f"Circuit {circuit} recorded failure {failure_count}/5")
            time.sleep(0.2)
        
        # Transition to open
        track_circuit_breaker(circuit, "open", 5)
        logger.info(f"Circuit {circuit} transitioned to OPEN state")
        time.sleep(1)
        
        # Transition to half-open to test recovery
        track_circuit_breaker(circuit, "half_open", 5)
        logger.info(f"Circuit {circuit} transitioned to HALF-OPEN state")
        time.sleep(0.5)
        
        # If recovery succeeds, go back to closed
        if random.choice([True, False]):
            track_circuit_breaker(circuit, "closed", 0)
            logger.info(f"Circuit {circuit} recovered and transitioned to CLOSED state")
        else:
            # Otherwise, go back to open
            track_circuit_breaker(circuit, "open", 6)
            logger.info(f"Circuit {circuit} failed recovery and returned to OPEN state")
        
        time.sleep(0.3)


def print_monitoring_stats():
    """Print current monitoring statistics."""
    logger.info("\n=== Current API Stats ===")
    stats = api_monitor.get_api_stats()
    for endpoint, stat in stats.items():
        logger.info(f"  {endpoint}:")
        logger.info(f"    Success: {stat.success_count}, Errors: {stat.error_count}, Retries: {stat.retry_count}")
        logger.info(f"    Avg response time: {stat.average_response_time:.4f}s")
        logger.info(f"    Rate limit hits: {stat.rate_limit_hits}")
    
    logger.info("\n=== Current Rate Limits ===")
    limits = api_monitor.get_rate_limits()
    for endpoint, limit in limits.items():
        if limit.limit > 0:
            percent_used = ((limit.limit - limit.remaining) / limit.limit) * 100
            logger.info(f"  {endpoint}: {limit.remaining}/{limit.limit} remaining ({percent_used:.1f}% used)")
            if limit.reset_time:
                logger.info(f"    Resets at: {limit.reset_time}")
    
    logger.info("\n=== Current Circuit Breaker States ===")
    circuits = api_monitor.get_circuit_stats()
    for name, circuit in circuits.items():
        logger.info(f"  {name}:")
        logger.info(f"    State: {circuit.current_state}")
        logger.info(f"    Failures: {circuit.failure_count}")
        logger.info(f"    State changes: {circuit.state_change_count}")
        if circuit.last_state_change:
            logger.info(f"    Last state change: {circuit.last_state_change}")


def main():
    """Main test function."""
    logger.info("Starting standalone monitoring system test...")
    
    # Reset monitoring stats
    api_monitor.reset_stats()
    
    # Simulate successful API calls
    logger.info("Simulating successful API calls...")
    endpoints = [
        "/api/users", 
        "/api/orders", 
        "/api/products", 
        "/api/rate-limited/resource"
    ]
    
    for _ in range(10):
        endpoint = random.choice(endpoints)
        simulate_api_call(endpoint, success=True)
    
    # Simulate some failed API calls
    logger.info("Simulating failed API calls...")
    for _ in range(5):
        endpoint = random.choice(endpoints)
        simulate_api_call(endpoint, success=False, retries=random.randint(0, 3))
    
    # Simulate circuit breaker state changes
    simulate_circuit_breaker_states()
    
    # Print monitoring stats
    print_monitoring_stats()
    
    # Generate a summary of system health
    logger.info("\n=== System Health Summary ===")
    stats = api_monitor.get_api_stats()
    
    total_calls = sum(stat.total_count for stat in stats.values())
    total_errors = sum(stat.error_count for stat in stats.values())
    error_rate = (total_errors / total_calls) * 100 if total_calls > 0 else 0
    
    circuits = api_monitor.get_circuit_stats()
    open_circuits = [c for c in circuits.values() if c.current_state == "open"]
    
    logger.info(f"Total API calls: {total_calls}")
    logger.info(f"Error rate: {error_rate:.1f}%")
    logger.info(f"Open circuits: {len(open_circuits)}/{len(circuits)}")
    
    if open_circuits:
        logger.info("WARNING: Some circuits are open, indicating service issues")
    
    if error_rate > 10:
        logger.info("WARNING: High error rate detected")
    else:
        logger.info("System appears healthy")
    
    logger.info("\nMonitoring system test complete!")


if __name__ == "__main__":
    main()