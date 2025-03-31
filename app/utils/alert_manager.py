"""
Alert Manager for REanna Router CRM integration.

This module provides functionality for detecting and alerting on repeated
sync failures, rate limit issues, and circuit breaker state changes.
"""

import logging
import json
import smtplib
import asyncio
import requests
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Callable
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pydantic import BaseModel, EmailStr, HttpUrl

logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    """Alert severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class AlertType(Enum):
    """Types of alerts that can be triggered"""
    REPEATED_SYNC_FAILURE = "REPEATED_SYNC_FAILURE"
    CIRCUIT_BREAKER_OPEN = "CIRCUIT_BREAKER_OPEN"
    RATE_LIMIT_CRITICAL = "RATE_LIMIT_CRITICAL"
    AUTH_FAILURE = "AUTH_FAILURE"
    INTEGRATION_ERROR = "INTEGRATION_ERROR"
    HEALTH_CHECK = "HEALTH_CHECK"

class AlertMethod(Enum):
    """Methods for delivering alerts"""
    LOG = "LOG"
    EMAIL = "EMAIL"
    WEBHOOK = "WEBHOOK"
    SLACK = "SLACK"

class AlertConfig(BaseModel):
    """Configuration for an alert"""
    enabled: bool = True
    type: AlertType
    level: AlertLevel = AlertLevel.WARNING
    threshold: int = 3  # Number of failures before alerting
    window_minutes: int = 60  # Time window for counting failures
    methods: List[AlertMethod] = [AlertMethod.LOG]
    recipients: List[str] = []  # Email addresses or webhook URLs
    cooldown_minutes: int = 30  # Minimum time between repeated alerts

class AlertEvent(BaseModel):
    """Details of an alert event"""
    id: str
    type: AlertType
    level: AlertLevel
    message: str
    details: Dict[str, Any] = {}
    timestamp: datetime = datetime.utcnow()
    entity_id: Optional[str] = None
    entity_type: Optional[str] = None
    operation_ids: List[str] = []

class EmailConfig(BaseModel):
    """Configuration for email alerts"""
    smtp_server: str = "smtp.example.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    sender: EmailStr = "alerts@reannarouter.example.com"
    use_tls: bool = True

class WebhookConfig(BaseModel):
    """Configuration for webhook alerts"""
    default_url: HttpUrl = "https://example.com/webhook"
    headers: Dict[str, str] = {"Content-Type": "application/json"}
    timeout_seconds: int = 10

class SlackConfig(BaseModel):
    """Configuration for Slack alerts"""
    webhook_url: HttpUrl = "https://hooks.slack.com/services/..."
    channel: str = "#alerts"
    username: str = "REanna Router Alert"
    icon_emoji: str = ":warning:"
    timeout_seconds: int = 10

class AlertManager:
    """
    Manager for detecting and sending alerts based on monitoring data.
    
    This class tracks operation failures, detects patterns that exceed
    alert thresholds, and sends notifications through configured channels.
    """
    
    def __init__(self):
        """Initialize the alert manager"""
        # Alert configurations
        self._configs: Dict[AlertType, AlertConfig] = {}
        
        # Default configurations
        self._setup_default_configs()
        
        # Notification method configurations
        self.email_config = EmailConfig()
        self.webhook_config = WebhookConfig()
        self.slack_config = SlackConfig()
        
        # Failure tracking
        self._failure_counts: Dict[str, Dict[str, int]] = {}  # {entity_id: {operation_type: count}}
        self._failure_timestamps: Dict[str, Dict[str, List[datetime]]] = {}  # {entity_id: {operation_type: [timestamps]}}
        
        # Already alerted entities (for cooldown)
        self._alerted_entities: Dict[str, Dict[str, datetime]] = {}  # {entity_id: {alert_type: last_alert_time}}
        
        # Set up default alert handler mapping
        self._alert_handlers: Dict[AlertMethod, Callable] = {
            AlertMethod.LOG: self._send_log_alert,
            AlertMethod.EMAIL: self._send_email_alert,
            AlertMethod.WEBHOOK: self._send_webhook_alert,
            AlertMethod.SLACK: self._send_slack_alert
        }
        
    def _setup_default_configs(self):
        """Set up default alert configurations"""
        default_configs = [
            AlertConfig(
                type=AlertType.REPEATED_SYNC_FAILURE,
                level=AlertLevel.ERROR,
                threshold=3,
                window_minutes=60,
                methods=[AlertMethod.LOG, AlertMethod.EMAIL],
                recipients=[]
            ),
            AlertConfig(
                type=AlertType.CIRCUIT_BREAKER_OPEN,
                level=AlertLevel.ERROR,
                threshold=1,
                window_minutes=30,
                methods=[AlertMethod.LOG, AlertMethod.EMAIL],
                recipients=[]
            ),
            AlertConfig(
                type=AlertType.RATE_LIMIT_CRITICAL,
                level=AlertLevel.WARNING,
                threshold=2,
                window_minutes=30,
                methods=[AlertMethod.LOG],
                recipients=[]
            ),
            AlertConfig(
                type=AlertType.AUTH_FAILURE,
                level=AlertLevel.CRITICAL,
                threshold=2,
                window_minutes=30,
                methods=[AlertMethod.LOG, AlertMethod.EMAIL],
                recipients=[]
            ),
            AlertConfig(
                type=AlertType.INTEGRATION_ERROR,
                level=AlertLevel.WARNING,
                threshold=5,
                window_minutes=60,
                methods=[AlertMethod.LOG],
                recipients=[]
            ),
            AlertConfig(
                type=AlertType.HEALTH_CHECK,
                level=AlertLevel.INFO,
                threshold=1,
                window_minutes=1440,  # 24 hours
                methods=[AlertMethod.LOG],
                recipients=[]
            )
        ]
        
        for config in default_configs:
            self._configs[config.type] = config
            
    def get_configs(self) -> Dict[str, AlertConfig]:
        """
        Get all alert configurations
        
        Returns:
            Dict of alert configurations with type as key
        """
        return {alert_type.value: config for alert_type, config in self._configs.items()}
    
    def get_config(self, alert_type: AlertType) -> Optional[AlertConfig]:
        """
        Get a specific alert configuration
        
        Args:
            alert_type: The type of alert to get configuration for
            
        Returns:
            Alert configuration if found, None otherwise
        """
        return self._configs.get(alert_type)
        
    def update_config(self, alert_type: AlertType, config: AlertConfig) -> bool:
        """
        Update an alert configuration
        
        Args:
            alert_type: The type of alert to update
            config: New configuration
            
        Returns:
            True if updated successfully, False otherwise
        """
        if config.type != alert_type:
            return False
            
        self._configs[alert_type] = config
        return True
        
    def update_email_config(self, config: EmailConfig) -> None:
        """
        Update email configuration
        
        Args:
            config: New email configuration
        """
        self.email_config = config
        
    def update_webhook_config(self, config: WebhookConfig) -> None:
        """
        Update webhook configuration
        
        Args:
            config: New webhook configuration
        """
        self.webhook_config = config
        
    def update_slack_config(self, config: SlackConfig) -> None:
        """
        Update Slack configuration
        
        Args:
            config: New Slack configuration
        """
        self.slack_config = config
        
    def record_operation_failure(self, 
                                entity_id: str, 
                                entity_type: str,
                                operation_type: str,
                                error: str,
                                operation_id: str,
                                details: Dict[str, Any] = None) -> bool:
        """
        Record a failed operation and check if it exceeds alert thresholds
        
        Args:
            entity_id: ID of the entity (e.g., tour_id, property_id)
            entity_type: Type of entity (e.g., 'tour', 'feedback')
            operation_type: Type of operation (e.g., 'sync', 'notification')
            error: Error message
            operation_id: ID of the failed operation
            details: Additional details about the failure
            
        Returns:
            True if an alert was triggered, False otherwise
        """
        now = datetime.utcnow()
        
        # Initialize tracking structures if needed
        if entity_id not in self._failure_counts:
            self._failure_counts[entity_id] = {}
            self._failure_timestamps[entity_id] = {}
            
        if operation_type not in self._failure_counts[entity_id]:
            self._failure_counts[entity_id][operation_type] = 0
            self._failure_timestamps[entity_id][operation_type] = []
            
        # Record this failure
        self._failure_counts[entity_id][operation_type] += 1
        self._failure_timestamps[entity_id][operation_type].append(now)
        
        # Determine alert type based on error
        alert_type = self._determine_alert_type(error)
        
        # Get configuration for this alert type
        config = self._configs.get(alert_type)
        if not config or not config.enabled:
            return False
            
        # Check if we've already alerted recently (cooldown)
        if self._is_in_cooldown(entity_id, alert_type):
            return False
            
        # Check if we've exceeded the threshold in the time window
        if self._check_threshold_exceeded(entity_id, operation_type, config):
            # Generate and send alert
            return self._generate_and_send_alert(
                alert_type=alert_type,
                entity_id=entity_id,
                entity_type=entity_type,
                operation_type=operation_type,
                error=error,
                operation_id=operation_id,
                details=details
            )
            
        return False
        
    def _determine_alert_type(self, error: str) -> AlertType:
        """
        Determine the alert type based on the error message
        
        Args:
            error: Error message
            
        Returns:
            AlertType
        """
        error_lower = error.lower()
        
        if "circuit" in error_lower and "open" in error_lower:
            return AlertType.CIRCUIT_BREAKER_OPEN
        elif "rate limit" in error_lower:
            return AlertType.RATE_LIMIT_CRITICAL
        elif "auth" in error_lower or "token" in error_lower or "credentials" in error_lower:
            return AlertType.AUTH_FAILURE
        else:
            return AlertType.REPEATED_SYNC_FAILURE
            
    def _is_in_cooldown(self, entity_id: str, alert_type: AlertType) -> bool:
        """
        Check if an entity is in the alert cooldown period
        
        Args:
            entity_id: Entity ID
            alert_type: Alert type
            
        Returns:
            True if in cooldown, False otherwise
        """
        now = datetime.utcnow()
        
        if entity_id not in self._alerted_entities:
            return False
            
        if alert_type.value not in self._alerted_entities[entity_id]:
            return False
            
        last_alert = self._alerted_entities[entity_id][alert_type.value]
        config = self._configs[alert_type]
        
        # Check if we're still in cooldown period
        return (now - last_alert).total_seconds() < (config.cooldown_minutes * 60)
        
    def _check_threshold_exceeded(self, entity_id: str, operation_type: str, config: AlertConfig) -> bool:
        """
        Check if failures exceed threshold in time window
        
        Args:
            entity_id: Entity ID
            operation_type: Operation type
            config: Alert configuration
            
        Returns:
            True if threshold exceeded, False otherwise
        """
        # Get timestamps in the window
        now = datetime.utcnow()
        window_start = now - timedelta(minutes=config.window_minutes)
        
        recent_failures = [
            ts for ts in self._failure_timestamps[entity_id][operation_type]
            if ts >= window_start
        ]
        
        # Clean up old timestamps
        self._failure_timestamps[entity_id][operation_type] = recent_failures
        
        # Check if we've exceeded threshold
        return len(recent_failures) >= config.threshold
        
    def _generate_and_send_alert(self,
                               alert_type: AlertType,
                               entity_id: str,
                               entity_type: str,
                               operation_type: str,
                               error: str,
                               operation_id: str,
                               details: Dict[str, Any] = None) -> bool:
        """
        Generate and send an alert
        
        Args:
            alert_type: Type of alert
            entity_id: Entity ID
            entity_type: Entity type
            operation_type: Operation type
            error: Error message
            operation_id: Operation ID
            details: Additional details
            
        Returns:
            True if alert sent successfully, False otherwise
        """
        import uuid
        
        config = self._configs[alert_type]
        
        # Create alert event
        event = AlertEvent(
            id=str(uuid.uuid4()),
            type=alert_type,
            level=config.level,
            message=f"Repeated {operation_type} failures for {entity_type} {entity_id}: {error}",
            details=details or {},
            entity_id=entity_id,
            entity_type=entity_type,
            operation_ids=[operation_id]
        )
        
        # Track that we've alerted on this entity
        if entity_id not in self._alerted_entities:
            self._alerted_entities[entity_id] = {}
            
        self._alerted_entities[entity_id][alert_type.value] = datetime.utcnow()
        
        # Send alerts for each configured method
        success = True
        
        for method in config.methods:
            handler = self._alert_handlers.get(method)
            if handler:
                try:
                    handler(event, config.recipients)
                except Exception as e:
                    logger.error(f"Error sending {method.value} alert: {str(e)}")
                    success = False
                    
        return success
        
    def _send_log_alert(self, event: AlertEvent, recipients: List[str]) -> None:
        """
        Send an alert to the logs
        
        Args:
            event: Alert event
            recipients: Ignored for log alerts
        """
        log_message = (
            f"ALERT {event.level.value}: {event.message} "
            f"(Type: {event.type.value}, ID: {event.id})"
        )
        
        if event.level == AlertLevel.INFO:
            logger.info(log_message)
        elif event.level == AlertLevel.WARNING:
            logger.warning(log_message)
        elif event.level == AlertLevel.ERROR:
            logger.error(log_message)
        elif event.level == AlertLevel.CRITICAL:
            logger.critical(log_message)
        
    def _send_email_alert(self, event: AlertEvent, recipients: List[str]) -> None:
        """
        Send an alert via email
        
        Args:
            event: Alert event
            recipients: Email recipients
        """
        if not recipients:
            logger.warning("No email recipients configured for alert")
            return
            
        # Create email
        msg = MIMEMultipart()
        msg['From'] = self.email_config.sender
        msg['To'] = ', '.join(recipients)
        msg['Subject'] = f"[{event.level.value}] REanna Router Alert: {event.type.value}"
        
        # Email body
        body = f"""
        <html>
        <body>
            <h2>{event.level.value} Alert: {event.type.value}</h2>
            <p><strong>Time:</strong> {event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
            <p><strong>Message:</strong> {event.message}</p>
            <p><strong>Entity:</strong> {event.entity_type} ({event.entity_id})</p>
            <h3>Details:</h3>
            <pre>{json.dumps(event.details, indent=2)}</pre>
            <p>
            <a href="http://localhost:8000/dashboard">View Dashboard</a>
            </p>
        </body>
        </html>
        """
        
        msg.attach(MIMEText(body, 'html'))
        
        # Send email
        try:
            server = smtplib.SMTP(self.email_config.smtp_server, self.email_config.smtp_port)
            if self.email_config.use_tls:
                server.starttls()
            
            if self.email_config.username and self.email_config.password:
                server.login(self.email_config.username, self.email_config.password)
                
            server.send_message(msg)
            server.quit()
            logger.info(f"Email alert sent to {len(recipients)} recipients")
        except Exception as e:
            logger.error(f"Failed to send email alert: {str(e)}")
            raise
        
    def _send_webhook_alert(self, event: AlertEvent, recipients: List[str]) -> None:
        """
        Send an alert via webhook
        
        Args:
            event: Alert event
            recipients: Webhook URLs
        """
        if not recipients:
            # Use default URL if no specific recipients
            recipients = [str(self.webhook_config.default_url)]
            
        # Prepare payload
        payload = {
            "id": event.id,
            "type": event.type.value,
            "level": event.level.value,
            "message": event.message,
            "timestamp": event.timestamp.isoformat(),
            "entity_id": event.entity_id,
            "entity_type": event.entity_type,
            "details": event.details
        }
        
        # Send to each webhook
        for webhook_url in recipients:
            try:
                response = requests.post(
                    webhook_url,
                    json=payload,
                    headers=self.webhook_config.headers,
                    timeout=self.webhook_config.timeout_seconds
                )
                response.raise_for_status()
                logger.info(f"Webhook alert sent to {webhook_url} (Status: {response.status_code})")
            except Exception as e:
                logger.error(f"Failed to send webhook alert to {webhook_url}: {str(e)}")
                raise
        
    def _send_slack_alert(self, event: AlertEvent, recipients: List[str]) -> None:
        """
        Send an alert via Slack
        
        Args:
            event: Alert event
            recipients: Slack channels (if empty, uses default from config)
        """
        # Use configured channels if none specified
        channels = recipients if recipients else [self.slack_config.channel]
        
        # Color coding based on alert level
        color_map = {
            AlertLevel.INFO: "#36a64f",  # green
            AlertLevel.WARNING: "#ffcc00",  # yellow
            AlertLevel.ERROR: "#ff9900",  # orange
            AlertLevel.CRITICAL: "#ff0000"  # red
        }
        
        # Prepare Slack message
        payload = {
            "channel": channels[0],  # Use first channel
            "username": self.slack_config.username,
            "icon_emoji": self.slack_config.icon_emoji,
            "attachments": [
                {
                    "fallback": f"{event.level.value} Alert: {event.message}",
                    "color": color_map.get(event.level, "#36a64f"),
                    "title": f"{event.level.value} Alert: {event.type.value}",
                    "text": event.message,
                    "fields": [
                        {
                            "title": "Entity",
                            "value": f"{event.entity_type} ({event.entity_id})",
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": event.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC'),
                            "short": True
                        }
                    ],
                    "actions": [
                        {
                            "type": "button",
                            "text": "View Dashboard",
                            "url": "http://localhost:8000/dashboard"
                        }
                    ]
                }
            ]
        }
        
        # Add details if available
        if event.details:
            payload["attachments"][0]["fields"].append({
                "title": "Details",
                "value": f"```{json.dumps(event.details, indent=2)}```",
                "short": False
            })
        
        # Send to Slack
        try:
            response = requests.post(
                str(self.slack_config.webhook_url),
                json=payload,
                timeout=self.slack_config.timeout_seconds
            )
            response.raise_for_status()
            logger.info(f"Slack alert sent to {channels[0]} (Status: {response.status_code})")
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {str(e)}")
            raise

# Global alert manager instance
alert_manager = AlertManager()