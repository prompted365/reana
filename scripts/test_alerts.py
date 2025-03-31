#!/usr/bin/env python3
"""
Quick test script to demonstrate the alert system functionality.

This script:
1. Simulates repeated operation failures
2. Triggers alerts based on configured thresholds
3. Shows alert notifications in the dashboard

Usage:
    python scripts/test_alerts.py
"""

import sys
import os
import asyncio
import uuid
import logging
import json
from datetime import datetime, timedelta

# Add the parent directory to the path so we can import app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.alert_manager import alert_manager, AlertType, AlertLevel, AlertMethod, AlertConfig
from app.api.routes.monitoring import FailedOperation, failed_operations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def configure_alert_system():
    """Configure alert thresholds for testing"""
    
    # Set lower thresholds for testing
    sync_failure_config = AlertConfig(
        type=AlertType.REPEATED_SYNC_FAILURE,
        level=AlertLevel.ERROR,
        threshold=2,  # Trigger after just 2 failures for testing
        window_minutes=5,  # Within 5 minutes
        methods=[AlertMethod.LOG],  # Use log only for testing
        recipients=[],
        cooldown_minutes=1  # Short cooldown for testing
    )
    alert_manager.update_config(AlertType.REPEATED_SYNC_FAILURE, sync_failure_config)
    
    # Configure circuit breaker alert
    circuit_breaker_config = AlertConfig(
        type=AlertType.CIRCUIT_BREAKER_OPEN,
        level=AlertLevel.ERROR,
        threshold=1,  # Trigger immediately
        window_minutes=5,
        methods=[AlertMethod.LOG],
        recipients=[],
        cooldown_minutes=1
    )
    alert_manager.update_config(AlertType.CIRCUIT_BREAKER_OPEN, circuit_breaker_config)
    
    logger.info("Alert system configured with test thresholds")

async def generate_test_failures():
    """Generate test failures to trigger alerts"""
    
    # Different entity IDs with failures
    entities = [
        {"id": "tour_12345", "type": "tour", "name": "Tour Sync - Property #12345"},
        {"id": "feedback_54321", "type": "feedback", "name": "Feedback Sync - Client #54321"},
        {"id": "booking_98765", "type": "booking", "name": "Booking Sync - Property #98765"}
    ]
    
    # Different error types
    error_types = [
        "API Connection Timeout", 
        "Rate Limit Exceeded", 
        "Authentication Failure",
        "Circuit Breaker Open: Service unavailable",
        "Invalid Response Format"
    ]
    
    # Clear existing failed operations
    failed_operations.clear()
    
    # Generate multiple failures for the first entity to trigger alert
    entity = entities[0]
    logger.info(f"Generating repeated failures for {entity['type']} {entity['id']}")
    
    for i in range(3):  # 3 failures should trigger alert with threshold of 2
        op_id = str(uuid.uuid4())
        error = error_types[i % len(error_types)]
        
        # Create failed operation
        operation = FailedOperation(
            id=op_id,
            operation=f"{entity['name']} - Attempt {i+1}",
            type=f"{entity['type']}-sync",
            status="FAILED",
            last_attempt=datetime.now() - timedelta(minutes=i),
            retry_count=i,
            error=error,
            data={"entity_id": entity['id'], "test": True}
        )
        
        # Register in failed operations
        failed_operations[op_id] = operation
        
        # Log the failure
        logger.info(f"Generated failure {i+1} for {entity['type']} {entity['id']}: {error}")
        
        # Record failure in alert manager - this should trigger an alert after the 2nd failure
        alert_triggered = alert_manager.record_operation_failure(
            entity_id=entity['id'],
            entity_type=entity['type'],
            operation_type=f"{entity['type']}_sync",
            error=error,
            operation_id=op_id,
            details={"entity_id": entity['id'], "operation": entity['name'], "test": True}
        )
        
        logger.info(f"Alert triggered: {alert_triggered}")
        
        # Small delay between operations
        await asyncio.sleep(0.5)
    
    # Generate just one failure for the other entities (shouldn't trigger alerts)
    for entity in entities[1:]:
        op_id = str(uuid.uuid4())
        error = error_types[0]
        
        operation = FailedOperation(
            id=op_id,
            operation=entity['name'],
            type=f"{entity['type']}-sync",
            status="FAILED",
            last_attempt=datetime.now(),
            retry_count=0,
            error=error,
            data={"entity_id": entity['id'], "test": True}
        )
        
        failed_operations[op_id] = operation
        
        logger.info(f"Generated single failure for {entity['type']} {entity['id']}")
        
        alert_triggered = alert_manager.record_operation_failure(
            entity_id=entity['id'],
            entity_type=entity['type'],
            operation_type=f"{entity['type']}_sync",
            error=error,
            operation_id=op_id,
            details={"entity_id": entity['id'], "operation": entity['name'], "test": True}
        )
        
        logger.info(f"Alert triggered: {alert_triggered}")
        
        await asyncio.sleep(0.5)

async def simulate_circuit_breaker_open():
    """Simulate a circuit breaker open event to trigger an alert"""
    
    logger.info("Simulating circuit breaker open event")
    
    entity_id = "api_rollout"
    error = "Circuit Breaker Open: Too many failures"
    op_id = str(uuid.uuid4())
    
    alert_triggered = alert_manager.record_operation_failure(
        entity_id=entity_id,
        entity_type="circuit_breaker",
        operation_type="api_call",
        error=error,
        operation_id=op_id,
        details={"circuit": "rollout_api", "failures": 5, "threshold": 3}
    )
    
    logger.info(f"Circuit breaker alert triggered: {alert_triggered}")

async def print_dashboard_instructions():
    """Print instructions for using the dashboard"""
    
    logger.info("\n" + "="*80)
    logger.info("TEST COMPLETED: Alerts have been generated")
    logger.info("="*80)
    logger.info("\nTo view the alerts in the dashboard:")
    logger.info("1. Start the FastAPI server if not running:")
    logger.info("   uvicorn app.main:app --reload")
    logger.info("\n2. Open the dashboard in your browser:")
    logger.info("   http://localhost:8000/dashboard")
    logger.info("\n3. Navigate to the 'Alerts' section in the dashboard")
    logger.info("   You should see alerts for repeated sync failures and circuit breaker events")
    logger.info("\n4. You can also check the API directly:")
    logger.info("   http://localhost:8000/api/monitoring/alerts")
    logger.info("="*80)

async def main():
    """Main test function"""
    
    logger.info("Starting alert system test")
    logger.info("====================================================")
    logger.info("This test demonstrates the alert system by:")
    logger.info("1. Configuring alert thresholds for testing")
    logger.info("2. Generating simulated failures to trigger alerts")
    logger.info("3. Simulating a circuit breaker open event")
    logger.info("4. Showing how to view results in the dashboard")
    logger.info("====================================================")
    
    try:
        # Configure alert thresholds for testing
        logger.info("\n[STEP 1] Configuring alert thresholds for testing")
        await configure_alert_system()
        
        # Generate test failures to trigger alerts
        logger.info("\n[STEP 2] Generating test failures to trigger alerts")
        await generate_test_failures()
        
        # Simulate circuit breaker open event
        logger.info("\n[STEP 3] Simulating circuit breaker open event")
        await simulate_circuit_breaker_open()
        
        # Print dashboard instructions
        logger.info("\n[STEP 4] Test completed - View results in dashboard")
        await print_dashboard_instructions()
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())