#!/usr/bin/env python3
"""
Test script for the monitoring system.

This script demonstrates:
1. API calls being tracked by the monitoring system
2. Rate limit tracking
3. Circuit breaker state changes and monitoring
4. Accessing monitoring data through API endpoints
"""

import sys
import os
import asyncio
import json
import random
import logging
from datetime import datetime
import aiohttp
from pprint import pprint

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.rollout_client import rollout_client, RolloutError, RolloutCircuitOpenError
from app.utils.monitoring import api_monitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def make_api_calls():
    """Make a series of API calls to generate monitoring data."""
    logger.info("Making API calls to generate monitoring data...")
    
    # List of endpoints to call
    endpoints = [
        "/connectors/",
        "/connectors/salesforce",
        "/connectors/hubspot",
        "/automations/"
    ]
    
    # Make several API calls to collect metrics
    for _ in range(3):
        for endpoint in endpoints:
            try:
                await rollout_client.call_api(endpoint)
                logger.info(f"Successfully called API endpoint: {endpoint}")
            except RolloutError as e:
                logger.error(f"Error calling API endpoint {endpoint}: {str(e)}")
            
            # Small delay between calls
            await asyncio.sleep(0.5)


async def make_mcp_calls():
    """Make a series of MCP tool calls to generate monitoring data."""
    logger.info("Making MCP tool calls to generate monitoring data...")
    
    # List of tools to call
    tools = [
        ("list_available_crms", {}),
        ("configure_rollout", {"apiKey": "test-key"}),
        ("configure_crm_connection", {"crmType": "hubspot", "credentialKey": "test-cred"}),
        ("sync_tour_data", {"tourData": {"tourId": "tour-123", "properties": []}})
    ]
    
    # Make several MCP tool calls to collect metrics
    for _ in range(2):
        for tool_name, arguments in tools:
            try:
                await rollout_client.call_mcp_tool(tool_name, arguments)
                logger.info(f"Successfully called MCP tool: {tool_name}")
            except RolloutError as e:
                logger.error(f"Error calling MCP tool {tool_name}: {str(e)}")
            
            # Small delay between calls
            await asyncio.sleep(0.5)


async def test_circuit_breaker():
    """Test circuit breaker functionality and monitoring."""
    logger.info("Testing circuit breaker functionality...")
    
    # Create a test endpoint that will always fail
    test_endpoint = "/test/will-fail"
    
    # Make calls until circuit breaker trips
    for i in range(10):
        try:
            await rollout_client.call_api(test_endpoint)
            logger.info("This call should have failed but didn't")
        except RolloutCircuitOpenError as e:
            logger.info(f"Circuit breaker open as expected: {str(e)}")
            break
        except RolloutError as e:
            logger.info(f"Call {i+1} failed as expected: {str(e)}")
        
        # Small delay between calls
        await asyncio.sleep(0.5)
    
    # Wait a bit for the circuit to potentially transition to half-open
    logger.info("Waiting for circuit breaker recovery timeout...")
    await asyncio.sleep(5)
    
    # Try another call to see if circuit is half-open
    try:
        await rollout_client.call_api(test_endpoint)
        logger.info("Call succeeded after circuit reset")
    except RolloutCircuitOpenError as e:
        logger.info(f"Circuit still open: {str(e)}")
    except RolloutError as e:
        logger.info(f"Circuit allowed test call but operation failed: {str(e)}")


async def check_monitoring_endpoints():
    """Call monitoring endpoints to get statistics."""
    logger.info("Checking monitoring endpoints...")
    
    base_url = "http://localhost:8000"
    endpoints = [
        "/api/monitoring/api-stats",
        "/api/monitoring/rate-limits",
        "/api/monitoring/circuit-states",
        "/api/monitoring/summary"
    ]
    
    async with aiohttp.ClientSession() as session:
        for endpoint in endpoints:
            url = f"{base_url}{endpoint}"
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Successfully retrieved monitoring data from {endpoint}")
                        logger.info("Sample data:")
                        pprint(data)
                    else:
                        logger.error(f"Failed to get monitoring data from {endpoint}: {response.status}")
            except Exception as e:
                logger.error(f"Error accessing monitoring endpoint {endpoint}: {str(e)}")
            
            # Small delay between calls
            await asyncio.sleep(0.5)


async def print_monitoring_stats():
    """Print current monitoring statistics directly from the monitor."""
    logger.info("Current API stats:")
    stats = api_monitor.get_api_stats()
    for endpoint, stat in stats.items():
        logger.info(f"  {endpoint}:")
        logger.info(f"    Success: {stat.success_count}, Errors: {stat.error_count}, Retries: {stat.retry_count}")
        logger.info(f"    Avg response time: {stat.average_response_time:.4f}s")
        logger.info(f"    Rate limit hits: {stat.rate_limit_hits}")
    
    logger.info("\nCurrent circuit breaker states:")
    circuits = api_monitor.get_circuit_stats()
    for name, circuit in circuits.items():
        logger.info(f"  {name}:")
        logger.info(f"    State: {circuit.current_state}")
        logger.info(f"    Failures: {circuit.failure_count}")
        logger.info(f"    State changes: {circuit.state_change_count}")
        if circuit.last_state_change:
            logger.info(f"    Last state change: {circuit.last_state_change}")
        if circuit.open_duration:
            logger.info(f"    Open duration: {circuit.open_duration}")


async def main():
    """Main test function."""
    logger.info("Starting monitoring system test...")
    
    # Reset monitoring stats
    api_monitor.reset_stats()
    
    # Make API and MCP calls to generate metrics
    await make_api_calls()
    await make_mcp_calls()
    
    # Test circuit breaker
    await test_circuit_breaker()
    
    # Print monitoring stats directly
    await print_monitoring_stats()
    
    # Check monitoring endpoints if API server is running
    try:
        await check_monitoring_endpoints()
    except Exception as e:
        logger.error(f"Error checking monitoring endpoints (API server might not be running): {str(e)}")
    
    logger.info("Monitoring system test complete!")


if __name__ == "__main__":
    asyncio.run(main())