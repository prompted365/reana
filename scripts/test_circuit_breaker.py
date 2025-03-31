#!/usr/bin/env python3
"""
Test Circuit Breaker Implementation for Rollout API

This script demonstrates the circuit breaker pattern implementation for the Rollout API.
It simulates API failures and shows how the circuit breaker works to prevent cascading failures.
"""

import asyncio
import logging
import sys
import time
from datetime import datetime

# Add the app directory to the path so we can import our modules
sys.path.append(".")

from app.services.rollout_client import rollout_client, RolloutError, RolloutCircuitOpenError
from app.utils.circuit_breaker import CircuitBreaker, CircuitState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("circuit-breaker-test")


# Mock API calls that will fail
async def mock_api_call(fail=False):
    """
    Mock a call to an API. Optionally fail the call.
    
    Args:
        fail: Whether to simulate a failure
        
    Returns:
        dict: Response data
    """
    if fail:
        raise RolloutError("Simulated API failure")
    return {"status": "success", "message": "Mock API call successful"}


# Test specific circuit breaker
async def test_specific_circuit_breaker():
    """Test a circuit breaker with specific configuration"""
    logger.info("\n=== Testing Specific Circuit Breaker ===\n")
    
    # Create a circuit breaker
    circuit = CircuitBreaker(
        name="test-circuit",
        failure_threshold=3,
        recovery_timeout=10,  # Short timeout for testing
        half_open_max_calls=2
    )
    
    # Function to run with circuit breaker
    async def run_with_circuit(should_fail=False):
        try:
            if not await circuit.allow_request():
                logger.warning("Circuit is open, request blocked")
                return False
                
            try:
                if should_fail:
                    raise RolloutError("Simulated failure")
                logger.info("Call succeeded")
                await circuit.record_success()
                return True
            except Exception as e:
                logger.error(f"Call failed: {str(e)}")
                await circuit.record_failure(e)
                return False
        except Exception as e:
            logger.error(f"Error using circuit: {str(e)}")
            return False
    
    # Run successful calls
    logger.info("1. Making successful calls...")
    await run_with_circuit(should_fail=False)
    await run_with_circuit(should_fail=False)
    
    # Run failing calls to trip the circuit
    logger.info("\n2. Making failing calls to trip the circuit...")
    await run_with_circuit(should_fail=True)
    await run_with_circuit(should_fail=True)
    await run_with_circuit(should_fail=True)  # This should trip the circuit
    
    # Verify circuit is open
    logger.info(f"\n3. Circuit state after failures: {circuit.state.value}")
    
    # Try to make calls with open circuit
    logger.info("\n4. Trying to make calls with open circuit...")
    await run_with_circuit(should_fail=False)
    await run_with_circuit(should_fail=False)
    
    # Wait for recovery timeout
    logger.info(f"\n5. Waiting for recovery timeout ({circuit._recovery_timeout}s)...")
    await asyncio.sleep(circuit.recovery_timeout + 1)
    
    logger.info(f"\n6. Circuit state after timeout: {circuit.state.value}")
    
    # Make successful calls in half-open state
    logger.info("\n7. Making successful calls in half-open state...")
    await run_with_circuit(should_fail=False)
    await run_with_circuit(should_fail=False)
    
    # Verify circuit is closed again
    logger.info(f"\n8. Circuit state after successful recovery: {circuit.state.value}")
    
    # Make more calls to verify normal operation
    logger.info("\n9. Making calls after recovery...")
    await run_with_circuit(should_fail=False)
    await run_with_circuit(should_fail=False)


# Test rolling window of failures
async def test_rollout_client_circuit_breaker():
    """Test the actual rollout client with circuit breaker protection"""
    logger.info("\n\n=== Testing Rollout Client Circuit Breaker ===\n")

    # Get initial state
    logger.info(f"Initial API circuit state: {rollout_client.api_circuit.state.value}")
    
    # Simulate API failures
    try:
        # Simulate connector details API calls
        logger.info("1. Making successful API call...")
        connector_details = await rollout_client.get_connector_details("test-connector")
        logger.info(f"   Result: {connector_details}")
        
        # Force the rollout client to fail by monkey patching the call_api method temporarily
        original_call_api = rollout_client.call_api
        
        async def failing_call_api(*args, **kwargs):
            raise RolloutError("Simulated API failure for testing")
        
        # Replace the method temporarily
        rollout_client.call_api = failing_call_api
        
        # Make failing calls to trip the circuit
        logger.info("\n2. Making failing API calls to trip the circuit...")
        try:
            for i in range(5):
                try:
                    await rollout_client.get_connector_details("test-connector")
                except RolloutError as e:
                    logger.info(f"   Expected error: {str(e)}")
        except RolloutCircuitOpenError as e:
            logger.info(f"   Circuit opened as expected: {str(e)}")
        
        # Check circuit state
        logger.info(f"\n3. API circuit state after failures: {rollout_client.api_circuit.state.value}")
        
        # Try making a call with open circuit
        logger.info("\n4. Trying API call with open circuit...")
        try:
            await rollout_client.get_connector_details("test-connector")
        except RolloutCircuitOpenError as e:
            logger.info(f"   Call blocked by circuit breaker as expected: {str(e)}")
        
        # Restore the original method to allow recovery
        rollout_client.call_api = original_call_api
        
        # Wait for circuit recovery
        timeout = rollout_client.api_circuit._recovery_timeout
        logger.info(f"\n5. Waiting for circuit recovery timeout ({timeout}s)...")
        await asyncio.sleep(timeout + 1)
        
        # Check circuit state
        logger.info(f"\n6. API circuit state after timeout: {rollout_client.api_circuit.state.value}")
        
        # Make successful call to recover
        logger.info("\n7. Making successful API call in half-open state...")
        connector_details = await rollout_client.get_connector_details("test-connector")
        logger.info(f"   Result: {connector_details}")
        
        # Check final circuit state
        logger.info(f"\n8. API circuit final state: {rollout_client.api_circuit.state.value}")
    
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
    finally:
        # Ensure original method is restored
        if hasattr(rollout_client, 'call_api') and rollout_client.call_api != original_call_api:
            rollout_client.call_api = original_call_api


async def main():
    """Main test function"""
    logger.info("Starting Circuit Breaker Tests")
    logger.info("=" * 80)
    
    # Run test with standalone circuit breaker
    await test_specific_circuit_breaker()
    
    # Test the rollout client's circuit breaker
    await test_rollout_client_circuit_breaker()
    
    logger.info("\n\nCircuit Breaker Tests Complete")
    logger.info("=" * 80)


if __name__ == "__main__":
    # Run the async tests
    asyncio.run(main())