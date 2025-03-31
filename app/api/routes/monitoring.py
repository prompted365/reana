"""
API routes for monitoring CRM integration system health

This module provides endpoints for monitoring:
1. API usage statistics
2. Rate limit consumption
3. Circuit breaker states
4. Performance metrics
5. Failed operation alerts and notifications
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import logging
import uuid
from pydantic import BaseModel, EmailStr, HttpUrl
from enum import Enum

from ...utils.monitoring import api_monitor
from ...utils.circuit_breaker import CircuitState
from ...utils.alert_manager import (
    alert_manager, 
    AlertType, 
    AlertLevel, 
    AlertMethod,
    AlertConfig,
    AlertEvent,
    EmailConfig,
    WebhookConfig,
    SlackConfig
)

# Define data models for failed operations
class FailedOperation(BaseModel):
    id: str
    operation: str
    type: str
    status: str
    last_attempt: datetime
    retry_count: int
    error: str
    data: Dict = {}

# Define request models for alert configuration
class UpdateAlertConfigRequest(BaseModel):
    enabled: bool = True
    threshold: int
    window_minutes: int
    methods: List[str]
    recipients: List[str]
    cooldown_minutes: int
    
class EmailConfigRequest(BaseModel):
    smtp_server: str
    smtp_port: int
    username: str
    password: str
    sender: EmailStr

# In-memory storage for failed operations (in a production app, this would be in a database)
failed_operations: Dict[str, FailedOperation] = {}

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/api/monitoring",
    tags=["monitoring"],
    responses={404: {"description": "Not found"}},
)


@router.get("/api-stats")
async def get_api_stats(endpoint: Optional[str] = None):
    """
    Get API usage statistics.
    
    Args:
        endpoint: Optional specific endpoint to filter by
        
    Returns:
        Dict of API statistics
    """
    try:
        stats = api_monitor.get_api_stats(endpoint)
        
        # Convert to serializable format
        result = {}
        for key, stat in stats.items():
            result[key] = {
                "endpoint": stat.endpoint,
                "success_count": stat.success_count,
                "error_count": stat.error_count,
                "retry_count": stat.retry_count,
                "total_count": stat.total_count,
                "average_response_time": stat.average_response_time,
                "percentile_95": stat.percentile_95,
                "rate_limit_hits": stat.rate_limit_hits,
                "last_called": stat.last_called.isoformat() if stat.last_called else None
            }
            
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting API stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving API statistics: {str(e)}")


@router.get("/rate-limits")
async def get_rate_limits(endpoint: Optional[str] = None):
    """
    Get rate limit information.
    
    Args:
        endpoint: Optional specific endpoint to filter by
        
    Returns:
        Dict of rate limit information
    """
    try:
        limits = api_monitor.get_rate_limits(endpoint)
        
        # Convert to serializable format
        result = {}
        for key, limit in limits.items():
            result[key] = {
                "endpoint": limit.endpoint,
                "limit": limit.limit,
                "remaining": limit.remaining,
                "reset_time": limit.reset_time.isoformat() if limit.reset_time else None,
                "last_updated": limit.last_updated.isoformat() if limit.last_updated else None,
                "percent_used": ((limit.limit - limit.remaining) / limit.limit) * 100 if limit.limit > 0 else 0
            }
            
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting rate limits: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving rate limit information: {str(e)}")


@router.get("/failed-operations")
async def get_failed_operations(operation_type: Optional[str] = None):
    """
    Get failed CRM sync operations.
    
    Args:
        operation_type: Optional filter by operation type (e.g., 'tour-sync', 'feedback-sync')
        
    Returns:
        List of failed operations
    """
    try:
        # Filter operations by type if specified
        if operation_type and operation_type != 'all':
            operations = [op for op in failed_operations.values() if op.type == operation_type]
        else:
            operations = list(failed_operations.values())
        
        # Sort by most recent first
        operations.sort(key=lambda op: op.last_attempt, reverse=True)
        
        return {
            "status": "success",
            "data": operations
        }
    except Exception as e:
        logger.error(f"Error getting failed operations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving failed operations: {str(e)}")


@router.post("/retry-operation/{operation_id}")
async def retry_operation(operation_id: str):
    """
    Retry a failed operation.
    
    Args:
        operation_id: ID of the operation to retry
        
    Returns:
        Status message
    """
    try:
        if operation_id not in failed_operations:
            raise HTTPException(status_code=404, detail=f"Operation with ID {operation_id} not found")
        
        # Update operation status
        operation = failed_operations[operation_id]
        operation.status = "PENDING_RETRY"
        operation.retry_count += 1
        operation.last_attempt = datetime.now()
        
        # Add alert if this is a repeated failure
        if operation.retry_count >= 3:
            alert_manager.record_operation_failure(
                entity_id=operation.data.get("entity_id", "unknown"),
                entity_type=operation.type,
                operation_type="retry",
                error=operation.error,
                operation_id=operation_id,
                details=operation.data
            )
        
        # In a real implementation, you would queue the operation for retry here
        # For example: task_queue.enqueue(retry_crm_sync, operation)
        
        logger.info(f"Operation {operation_id} queued for retry")
        
        return {
            "status": "success",
            "message": f"Operation {operation_id} queued for retry"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrying operation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrying operation: {str(e)}")


@router.delete("/delete-operation/{operation_id}")
async def delete_operation(operation_id: str):
    """
    Delete a failed operation.
    
    Args:
        operation_id: ID of the operation to delete
        
    Returns:
        Status message
    """
    try:
        if operation_id not in failed_operations:
            raise HTTPException(status_code=404, detail=f"Operation with ID {operation_id} not found")
        
        # Remove operation
        del failed_operations[operation_id]
        
        logger.info(f"Operation {operation_id} deleted")
        
        return {
            "status": "success",
            "message": f"Operation {operation_id} deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting operation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error deleting operation: {str(e)}")


@router.post("/retry-all-operations")
async def retry_all_operations(operation_type: Optional[str] = None):
    """
    Retry all failed operations.
    
    Args:
        operation_type: Optional filter by operation type
        
    Returns:
        Count of operations queued for retry
    """
    try:
        # Filter operations to retry
        operations_to_retry = []
        
        for op_id, operation in failed_operations.items():
            if operation.status == "FAILED":
                if not operation_type or operation_type == "all" or operation.type == operation_type:
                    operations_to_retry.append(op_id)
        
        # Update operation statuses
        for op_id in operations_to_retry:
            failed_operations[op_id].status = "PENDING_RETRY"
            failed_operations[op_id].retry_count += 1
            failed_operations[op_id].last_attempt = datetime.now()
        
        # In a real implementation, you would queue the operations for retry here
        
        logger.info(f"{len(operations_to_retry)} operations queued for retry")
        
        return {
            "status": "success",
            "count": len(operations_to_retry),
            "message": f"{len(operations_to_retry)} operations queued for retry"
        }
    except Exception as e:
        logger.error(f"Error retrying operations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrying operations: {str(e)}")


@router.post("/add-test-failed-operations")
async def add_test_failed_operations():
    """
    Add test failed operations for demonstration purposes.
    This endpoint is for testing only.
    
    Returns:
        Status message
    """
    try:
        # Clear existing operations
        failed_operations.clear()
        
        # Add some test operations
        test_operations = [
            {
                "id": str(uuid.uuid4()),
                "operation": "Tour Sync - Property #12345",
                "type": "tour-sync",
                "status": "FAILED",
                "last_attempt": datetime.now() - timedelta(minutes=30),
                "retry_count": 3,
                "error": "API Connection Timeout",
                "data": {"property_id": "12345", "tour_id": "T789", "entity_id": "12345"}
            },
            {
                "id": str(uuid.uuid4()),
                "operation": "Feedback Sync - Client #54321",
                "type": "feedback-sync",
                "status": "PENDING_RETRY",
                "last_attempt": datetime.now() - timedelta(hours=1),
                "retry_count": 2,
                "error": "Rate Limit Exceeded",
                "data": {"feedback_id": "F456", "client_id": "54321", "entity_id": "54321"}
            },
            {
                "id": str(uuid.uuid4()),
                "operation": "Tour Sync - Property #67890",
                "type": "tour-sync",
                "status": "FAILED",
                "last_attempt": datetime.now() - timedelta(hours=2),
                "retry_count": 5,
                "error": "Invalid Response Format",
                "data": {"property_id": "67890", "tour_id": "T123", "entity_id": "67890"}
            },
            {
                "id": str(uuid.uuid4()),
                "operation": "Feedback Sync - Client #98765",
                "type": "feedback-sync",
                "status": "FAILED",
                "last_attempt": datetime.now() - timedelta(minutes=45),
                "retry_count": 1,
                "error": "Authentication Failure",
                "data": {"feedback_id": "F789", "client_id": "98765", "entity_id": "98765"}
            }
        ]
        
        for op in test_operations:
            failed_operations[op["id"]] = FailedOperation(**op)
        
        return {
            "status": "success",
            "count": len(test_operations),
            "message": f"{len(test_operations)} test operations added"
        }
    except Exception as e:
        logger.error(f"Error adding test operations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adding test operations: {str(e)}")


@router.post("/register-failed-operation")
async def register_failed_operation(operation: FailedOperation):
    """
    Register a failed operation and trigger alerts if thresholds are exceeded.
    
    Args:
        operation: The failed operation details
        
    Returns:
        Status message and whether an alert was triggered
    """
    try:
        # Add to failed operations
        failed_operations[operation.id] = operation
        
        # Check alert thresholds
        alert_triggered = alert_manager.record_operation_failure(
            entity_id=operation.data.get("entity_id", "unknown"),
            entity_type=operation.type,
            operation_type=operation.operation,
            error=operation.error,
            operation_id=operation.id,
            details=operation.data
        )
        
        return {
            "status": "success",
            "message": f"Operation {operation.id} registered",
            "alert_triggered": alert_triggered
        }
    except Exception as e:
        logger.error(f"Error registering failed operation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error registering failed operation: {str(e)}")


@router.get("/alerts")
async def get_alerts(alert_type: Optional[str] = None, level: Optional[str] = None, 
                    since: Optional[datetime] = None):
    """
    Get triggered alerts filtered by type, level, and time range
    
    Args:
        alert_type: Optional filter by alert type
        level: Optional filter by alert level
        since: Optional filter for alerts since this time
        
    Returns:
        List of alert events
    """
    try:
        # Note: This is a stub implementation that would normally retrieve alerts
        # from a database. Since we haven't implemented alert storage yet,
        # we'll return a sample alert for demonstration.
        
        sample_alert = AlertEvent(
            id=str(uuid.uuid4()),
            type=AlertType.REPEATED_SYNC_FAILURE,
            level=AlertLevel.ERROR,
            message="Repeated tour sync failures for property",
            details={"failures": 3, "last_error": "API Connection Timeout"},
            entity_id="tour_12345",
            entity_type="tour",
            operation_ids=["op_" + str(uuid.uuid4())],
            timestamp=datetime.utcnow() - timedelta(minutes=30)
        )
        
        return {
            "status": "success",
            "data": [sample_alert]
        }
    except Exception as e:
        logger.error(f"Error getting alerts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving alerts: {str(e)}")


@router.get("/alert-configs")
async def get_alert_configs(alert_type: Optional[str] = None):
    """
    Get alert configurations
    
    Args:
        alert_type: Optional specific alert type
        
    Returns:
        Dict of alert configurations
    """
    try:
        configs = alert_manager.get_configs()
        
        # Filter by type if specified
        if alert_type:
            configs = {k: v for k, v in configs.items() if k == alert_type}
        
        return {
            "status": "success",
            "data": configs
        }
    except Exception as e:
        logger.error(f"Error getting alert configs: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving alert configurations: {str(e)}")


@router.put("/alert-configs/{alert_type}")
async def update_alert_config(alert_type: str, config: UpdateAlertConfigRequest):
    """
    Update an alert configuration
    
    Args:
        alert_type: Alert type to update
        config: New configuration
        
    Returns:
        Status message
    """
    try:
        # Convert string alert type to enum
        try:
            alert_type_enum = AlertType(alert_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid alert type: {alert_type}")
        
        # Get existing config
        existing_config = alert_manager.get_config(alert_type_enum)
        if not existing_config:
            raise HTTPException(status_code=404, detail=f"Alert type {alert_type} not found")
        
        # Convert string methods to enum
        methods = []
        for method in config.methods:
            try:
                methods.append(AlertMethod(method))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid alert method: {method}")
        
        # Create updated config
        updated_config = AlertConfig(
            type=alert_type_enum,
            level=existing_config.level,  # Keep existing level
            enabled=config.enabled,
            threshold=config.threshold,
            window_minutes=config.window_minutes,
            methods=methods,
            recipients=config.recipients,
            cooldown_minutes=config.cooldown_minutes
        )
        
        # Update config
        success = alert_manager.update_config(alert_type_enum, updated_config)
        if not success:
            raise HTTPException(status_code=500, detail="Failed to update alert configuration")
        
        return {
            "status": "success",
            "message": f"Alert configuration for {alert_type} updated successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating alert config: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating alert configuration: {str(e)}")


@router.put("/notification-settings/email")
async def update_email_settings(config: EmailConfigRequest):
    """
    Update email notification settings
    
    Args:
        config: Email configuration
        
    Returns:
        Status message
    """
    try:
        # Update email config
        email_config = EmailConfig(
            smtp_server=config.smtp_server,
            smtp_port=config.smtp_port,
            username=config.username,
            password=config.password,
            sender=config.sender,
            use_tls=True
        )
        
        alert_manager.update_email_config(email_config)
        
        return {
            "status": "success",
            "message": "Email notification settings updated successfully"
        }
    except Exception as e:
        logger.error(f"Error updating email settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error updating email settings: {str(e)}")


@router.post("/test-alert")
async def test_alert(alert_type: str, recipient: str):
    """
    Send a test alert to verify notification settings
    
    Args:
        alert_type: Type of alert to test
        recipient: Email address or webhook URL to send to
        
    Returns:
        Status message
    """
    try:
        # Convert string to enum
        try:
            alert_type_enum = AlertType(alert_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid alert type: {alert_type}")
        
        # Create test event
        event = AlertEvent(
            id=str(uuid.uuid4()),
            type=alert_type_enum,
            level=AlertLevel.INFO,
            message=f"Test alert for {alert_type}",
            entity_id="test_entity",
            entity_type="test",
            timestamp=datetime.utcnow()
        )
        
        # For test purposes, use all notification methods
        for method in AlertMethod:
            try:
                alert_manager._alert_handlers[method](event, [recipient])
                logger.info(f"Test alert sent via {method.value}")
            except Exception as e:
                logger.error(f"Error sending test alert via {method.value}: {str(e)}")
        
        return {
            "status": "success",
            "message": f"Test alert sent via all available methods"
        }
    except Exception as e:
        logger.error(f"Error sending test alert: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error sending test alert: {str(e)}")


@router.get("/circuit-states")
async def get_circuit_states(name: Optional[str] = None):
    """
    Get circuit breaker states.
    
    Args:
        name: Optional specific circuit breaker to filter by
        
    Returns:
        Dict of circuit breaker states
    """
    try:
        circuits = api_monitor.get_circuit_stats(name)
        
        # Convert to serializable format
        result = {}
        for key, circuit in circuits.items():
            result[key] = {
                "name": circuit.name,
                "current_state": circuit.current_state,
                "failure_count": circuit.failure_count,
                "state_change_count": circuit.state_change_count,
                "last_state_change": circuit.last_state_change.isoformat() if circuit.last_state_change else None,
                "last_failure": circuit.last_failure.isoformat() if circuit.last_failure else None,
                "last_success": circuit.last_success.isoformat() if circuit.last_success else None,
                "open_duration": str(circuit.open_duration) if circuit.open_duration else "0:00:00",
                "total_open_time": str(circuit.total_open_time) if circuit.total_open_time else "0:00:00"
            }
            
        return {
            "status": "success",
            "data": result
        }
    except Exception as e:
        logger.error(f"Error getting circuit states: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving circuit breaker states: {str(e)}")


@router.post("/reset-stats")
async def reset_stats():
    """
    Reset all monitoring statistics.
    
    Returns:
        Dict with status message
    """
    try:
        api_monitor.reset_stats()
        return {
            "status": "success",
            "message": "Monitoring statistics reset successfully"
        }
    except Exception as e:
        logger.error(f"Error resetting stats: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error resetting monitoring statistics: {str(e)}")


@router.get("/summary")
async def get_monitoring_summary():
    """
    Get a summary of all monitoring statistics.
    
    Returns:
        Dict containing summary of API stats, rate limits, and circuit states
    """
    try:
        # Get all statistics
        api_stats = api_monitor.get_api_stats()
        rate_limits = api_monitor.get_rate_limits()
        circuit_stats = api_monitor.get_circuit_stats()
        
        # Calculate summary statistics
        total_api_calls = sum(stat.total_count for stat in api_stats.values())
        total_errors = sum(stat.error_count for stat in api_stats.values())
        total_retries = sum(stat.retry_count for stat in api_stats.values())
        error_rate = (total_errors / total_api_calls) * 100 if total_api_calls > 0 else 0
        
        # Calculate average response time across all endpoints
        total_response_time = sum(stat.total_response_time for stat in api_stats.values())
        total_success_calls = sum(stat.success_count for stat in api_stats.values())
        avg_response_time = total_response_time / total_success_calls if total_success_calls > 0 else 0
        
        # Get circuit breaker status
        open_circuits = [c for c in circuit_stats.values() if c.current_state == "OPEN"]
        half_open_circuits = [c for c in circuit_stats.values() if c.current_state == "HALF_OPEN"]
        
        # Get rate limit status (find the closest to being exhausted)
        rate_limit_status = "HEALTHY"
        lowest_remaining_percent = 100
        for limit in rate_limits.values():
            if limit.limit > 0:
                remaining_percent = (limit.remaining / limit.limit) * 100
                if remaining_percent < lowest_remaining_percent:
                    lowest_remaining_percent = remaining_percent
                    
                if remaining_percent < 10:
                    rate_limit_status = "WARNING"
                if remaining_percent < 5:
                    rate_limit_status = "CRITICAL"
        
        # Determine overall system health
        system_health = "HEALTHY"
        if open_circuits or rate_limit_status == "CRITICAL":
            system_health = "DEGRADED"
        elif half_open_circuits or rate_limit_status == "WARNING" or error_rate > 10:
            system_health = "WARNING"
        
        # Get count of recent failed operations
        recent_failures = [
            op for op in failed_operations.values() 
            if op.status == "FAILED" and 
            op.last_attempt >= (datetime.now() - timedelta(hours=24))
        ]
        
        return {
            "status": "success",
            "data": {
                "system_health": system_health,
                "api_stats": {
                    "total_calls": total_api_calls,
                    "total_errors": total_errors,
                    "total_retries": total_retries,
                    "error_rate": error_rate,
                    "average_response_time": avg_response_time
                },
                "circuit_breakers": {
                    "total": len(circuit_stats),
                    "open": len(open_circuits),
                    "half_open": len(half_open_circuits),
                    "closed": len(circuit_stats) - len(open_circuits) - len(half_open_circuits)
                },
                "rate_limits": {
                    "status": rate_limit_status,
                    "lowest_remaining_percent": lowest_remaining_percent
                },
                "failed_operations": {
                    "recent_count": len(recent_failures),
                    "total_count": len(failed_operations)
                },
                "timestamp": datetime.utcnow().isoformat()
            }
        }
    except Exception as e:
        logger.error(f"Error getting monitoring summary: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error retrieving monitoring summary: {str(e)}")