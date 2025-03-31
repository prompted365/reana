# REanna Router Alert System Documentation

## Overview

The REanna Router Alert System monitors integration operations, detects patterns of failures, and sends notifications through configurable channels. It's designed to provide real-time visibility into system health and proactively notify stakeholders of issues requiring attention.

## Core Components

### 1. Alert Manager (`app/utils/alert_manager.py`)

The central component responsible for:
- Tracking operation failures by entity and type
- Detecting when failures exceed configurable thresholds
- Sending alerts through multiple channels
- Implementing cooldown periods to prevent alert flooding

#### Key Classes:
- `AlertLevel`: Defines severity levels (INFO, WARNING, ERROR, CRITICAL)
- `AlertType`: Categorizes alerts (REPEATED_SYNC_FAILURE, CIRCUIT_BREAKER_OPEN, etc.)
- `AlertMethod`: Defines notification channels (LOG, EMAIL, WEBHOOK, SLACK)
- `AlertConfig`: Configuration for thresholds, cooldown periods, and notification methods
- `AlertEvent`: Represents a triggered alert with details
- `AlertManager`: Main class that manages the alert system

### 2. Monitoring Routes (`app/api/routes/monitoring.py`)

Provides API endpoints for:
- Accessing failed operations data
- Managing alert configurations
- Testing alert notifications
- Getting system health statistics

#### Key Endpoints:
- `GET /api/monitoring/alerts`: List triggered alerts
- `GET /api/monitoring/alert-configs`: Get alert configurations
- `PUT /api/monitoring/alert-configs/{alert_type}`: Update alert configuration
- `GET /api/monitoring/failed-operations`: List failed operations
- `GET /api/monitoring/summary`: Get system health summary

### 3. Dashboard Integration (`app/templates/dashboard.html` and `app/static/js/dashboard.js`)

Visualizes the alert system with:
- A dedicated "Alerts & Notifications" section
- Tables showing recent alerts
- Configuration panels for alert settings
- A test form to send test alerts

## Alert Types

1. **REPEATED_SYNC_FAILURE**: Triggered when an entity experiences multiple sync failures within a time window
2. **CIRCUIT_BREAKER_OPEN**: Triggered when a circuit breaker opens due to repeated failures
3. **RATE_LIMIT_CRITICAL**: Triggered when rate limit consumption reaches critical levels
4. **AUTH_FAILURE**: Triggered when authentication issues occur multiple times
5. **INTEGRATION_ERROR**: Triggered for general integration errors occurring repeatedly
6. **HEALTH_CHECK**: Triggered for system health check failures

## Notification Methods

1. **LOG**: Writes alerts to the application logs with appropriate severity level
2. **EMAIL**: Sends formatted HTML emails to configured recipients
3. **WEBHOOK**: Posts alert data to configured webhook endpoints
4. **SLACK**: Sends formatted messages to Slack channels

## Configuration

Each alert type has a configurable:
- **Threshold**: Number of failures required to trigger the alert
- **Window**: Time period within which failures are counted
- **Methods**: Which notification methods to use
- **Recipients**: Where to send notifications
- **Cooldown**: Minimum time between repeated alerts for the same entity

## Testing

The alert system can be tested using:
- `scripts/test_alerts.py`: Creates sample failures to trigger alerts
- `scripts/test_circuit_breaker.py`: Tests circuit breaker integration
- Dashboard test form: Sends test alerts for verification

## Integration with Other Components

- **Circuit Breaker**: Alerts when circuit breakers open to protect the system
- **Rate Limiting**: Alerts when API rate limits approach exhaustion
- **Failed Operations Tracking**: Records operation failures for the dashboard
- **Notification Service**: Routes alerts to appropriate channels

## Usage Examples

### Recording Operation Failures

```python
# Record a failed operation that might trigger an alert
alert_triggered = alert_manager.record_operation_failure(
    entity_id="tour_12345",
    entity_type="tour",
    operation_type="sync_tour",
    error="API Connection Timeout",
    operation_id="op_abc123",
    details={"tour_id": "tour_12345", "agent_id": "agent_789"}
)
```

### Updating Alert Configuration

```python
# Configure lower thresholds for testing
config = AlertConfig(
    type=AlertType.REPEATED_SYNC_FAILURE,
    level=AlertLevel.ERROR,
    threshold=2,  # Trigger after just 2 failures
    window_minutes=5,  # Within 5 minutes
    methods=[AlertMethod.LOG, AlertMethod.EMAIL],
    recipients=["alerts@example.com"],
    cooldown_minutes=5
)
alert_manager.update_config(AlertType.REPEATED_SYNC_FAILURE, config)