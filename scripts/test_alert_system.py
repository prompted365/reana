#!/usr/bin/env python3
"""
Test script for the REanna Router Alert System.

This script tests the alert system by:
1. Generating test failed operations
2. Triggering alerts based on configurable thresholds
3. Testing notification delivery
4. Configuring and updating alert settings

Usage:
    python scripts/test_alert_system.py
"""

import asyncio
import sys
import json
import uuid
from datetime import datetime, timedelta
import logging
import os
from aiohttp import web
from typing import Dict, Any, List

# Add the parent directory to the path so we can import the app modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.alert_manager import (
    alert_manager,
    AlertType,
    AlertLevel,
    AlertMethod,
    AlertConfig,
    AlertEvent, 
    WebhookConfig,
    EmailConfig
)
from app.api.routes.monitoring import FailedOperation, failed_operations

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create a test webhook server to receive notifications
WEBHOOK_PORT = 8765
webhook_received_data = []

async def handle_webhook(request):
    """Simple webhook handler for testing"""
    data = await request.json()
    logger.info(f"Webhook received: {json.dumps(data, indent=2)}")
    webhook_received_data.append(data)
    return web.Response(text="OK")

async def start_webhook_server():
    """Start a simple webhook server for testing"""
    app = web.Application()
    app.router.add_post('/', handle_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, 'localhost', WEBHOOK_PORT)
    await site.start()
    logger.info(f"Webhook server started on http://localhost:{WEBHOOK_PORT}")
    return runner

async def stop_webhook_server(runner):
    """Stop the webhook server"""
    await runner.cleanup()

async def configure_alert_system():
    """Configure the alert system for testing"""
    # Configure webhook settings
    webhook_config = WebhookConfig(
        default_url=f"http://localhost:{WEBHOOK_PORT}",
        headers={"Content-Type": "application/json"},
        timeout_seconds=5
    )
    alert_manager.update_webhook_config(webhook_config)
    
    # Configure email settings (these are fake for testing)
    email_config = EmailConfig(
        smtp_server="smtp.example.com",
        smtp_port=587,
        username="test@example.com",
        password="password",
        sender="alerts@reannarouter.example.com",
        use_tls=True
    )
    alert_manager.update_email_config(email_config)
    
    # Configure alert thresholds
    sync_failure_config = AlertConfig(
        type=AlertType.REPEATED_SYNC_FAILURE,
        level=AlertLevel.ERROR,
        threshold=3,  # Trigger after 3 failures
        window_minutes=60,  # Within 60 minutes
        methods=[AlertMethod.LOG, AlertMethod.WEBHOOK],  # Use log and webhook
        recipients=[f"http://localhost:{WEBHOOK_PORT}"],
        cooldown_minutes=5  # Wait 5 minutes between alerts
    )
    alert_manager.update_config(AlertType.REPEATED_SYNC_FAILURE, sync_failure_config)
    
    # Configure circuit breaker alert
    circuit_breaker_config = AlertConfig(
        type=AlertType.CIRCUIT_BREAKER_OPEN,
        level=AlertLevel.ERROR,
        threshold=1,  # Trigger immediately
        window_minutes=30,
        methods=[AlertMethod.LOG, AlertMethod.WEBHOOK],
        recipients=[f"http://localhost:{WEBHOOK_PORT}"],
        cooldown_minutes=10
    )
    alert_manager.update_config(AlertType.CIRCUIT_BREAKER_OPEN, circuit_breaker_config)
    
    logger.info("Alert system configured")

async def generate_test_failures():
    """Generate test failures to trigger alerts"""
    property_id = "12345"
    entity_type = "tour"
    
    # Generate several failures for the same entity
    for i in range(5):
        op_id = str(uuid.uuid4())
        
        # Different error types for variety
        if i % 3 == 0:
            error = "API Connection Timeout"
        elif i % 3 == 1:
            error = "Rate Limit Exceeded"
        else:
            error = "Circuit Breaker Open: Service unavailable"
        
        # Create failed operation
        operation = FailedOperation(
            id=op_id,
            operation=f"Test Sync - Property #{property_id}",
            type="tour-sync",
            status="FAILED",
            last_attempt=datetime.now() - timedelta(minutes=i*10),
            retry_count=i,
            error=error,
            data={"property_id": property_id, "tour_id": f"T{i}", "entity_id": property_id}
        )
        
        # Register in failed operations
        failed_operations[op_id] = operation
        
        # Record failure in alert system
        alert_triggered = alert_manager.record_operation_failure(
            entity_id=property_id,
            entity_type=entity_type,
            operation_type="sync_tour",
            error=error,
            operation_id=op_id,
            details={"property_id": property_id, "test": True}
        )
        
        logger.info(f"Generated failure {i+1} for property {property_id}, alert triggered: {alert_triggered}")
        
        # Wait a bit between operations to simulate real-world timing
        await asyncio.sleep(1)
    
    logger.info(f"Generated {5} test failures")

async def show_alert_configs():
    """Show current alert configuration"""
    configs = alert_manager.get_configs()
    
    logger.info("Current Alert Configurations:")
    for alert_type, config in configs.items():
        logger.info(f"  {alert_type}:")
        logger.info(f"    Enabled: {config.enabled}")
        logger.info(f"    Level: {config.level.value}")
        logger.info(f"    Threshold: {config.threshold}")
        logger.info(f"    Window: {config.window_minutes} minutes")
        logger.info(f"    Methods: {[m.value for m in config.methods]}")
        logger.info(f"    Recipients: {config.recipients}")
        logger.info(f"    Cooldown: {config.cooldown_minutes} minutes")
        logger.info("")

async def send_test_alert():
    """Send a test alert to verify configuration"""
    event = AlertEvent(
        id=str(uuid.uuid4()),
        type=AlertType.REPEATED_SYNC_FAILURE,
        level=AlertLevel.ERROR,
        message="Test alert from test_alert_system.py",
        details={"test": True, "source": "test_script"},
        entity_id="test_entity",
        entity_type="test",
        operation_ids=["test_op_1"],
        timestamp=datetime.utcnow()
    )
    
    # Try all alert methods
    for method in AlertMethod:
        try:
            handler = alert_manager._alert_handlers.get(method)
            if handler:
                recipients = ["test@example.com"]
                if method == AlertMethod.WEBHOOK:
                    recipients = [f"http://localhost:{WEBHOOK_PORT}"]
                    
                handler(event, recipients)
                logger.info(f"Sent test alert via {method.value}")
        except Exception as e:
            logger.error(f"Error sending test alert via {method.value}: {str(e)}")

async def main():
    """Main test function"""
    logger.info("Starting alert system test")
    
    # Start webhook server if needed
    webhook_runner = None
    try:
        # Check if we can import aiohttp for webhook testing
        import aiohttp
        webhook_runner = await start_webhook_server()
    except ImportError:
        logger.warning("aiohttp not installed, webhook testing disabled")
    
    try:
        # Configure the alert system
        await configure_alert_system()
        
        # Show current configuration
        await show_alert_configs()
        
        # Generate test failures
        await generate_test_failures()
        
        # Send a test alert
        await send_test_alert()
        
        # Wait a bit to allow webhooks to be received
        if webhook_runner:
            logger.info("Waiting for webhook callbacks...")
            await asyncio.sleep(3)
            logger.info(f"Received {len(webhook_received_data)} webhook callbacks")
        
        logger.info("Alert system test completed successfully")
        
    except Exception as e:
        logger.error(f"Error during test: {str(e)}")
        raise
    finally:
        # Cleanup webhook server if started
        if webhook_runner:
            await stop_webhook_server(webhook_runner)

if __name__ == "__main__":
    # Check if we're running in an async environment or not
    try:
        asyncio.run(main())
    except RuntimeError:
        # Already running in an event loop
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())