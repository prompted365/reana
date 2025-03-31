"""
Notification Service

This module handles notification delivery for REanna Router, including
sending feedback to listing agents and syncing data with CRM systems.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import uuid

from ..models.database import get_db_connection
from ..models.feedback import Feedback
from ..utils.alert_manager import (
    alert_manager,
    AlertType,
    AlertLevel
)
from .rollout_client import (RolloutError, RolloutRateLimitError, 
                           RolloutServerError, RolloutCircuitOpenError)
from ..api.routes.monitoring import FailedOperation, failed_operations
from .rollout_client import rollout_client

# Configure logging
logger = logging.getLogger(__name__)


class NotificationService:
    """Service for sending notifications and syncing with CRMs"""
    
    def __init__(self, db):
        """
        Initialize the notification service
        
        Args:
            db: Database connection
        """
        self.db = db
        
    async def notify_listing_agent(self, 
                                  feedback_id: str, 
                                  sync_to_crm: bool = True) -> Dict[str, Any]:
        """
        Send feedback notification to listing agent and optionally sync to CRM
        
        Args:
            feedback_id: ID of the feedback to send
            sync_to_crm: Whether to sync the feedback to CRM systems
            
        Returns:
            Dict: Notification result
        """
        try:
            # Get feedback data
            feedback = await self.db.get_feedback(feedback_id)
            if not feedback:
                return {"success": False, "error": f"Feedback {feedback_id} not found"}
            
            # Get the task associated with the feedback
            task = await self.db.get_task(feedback.task_id)
            if not task:
                return {"success": False, "error": f"Task {feedback.task_id} not found"}
            
            # Get the property visit associated with the task
            property_visit = await self.db.get_property_visit(task.visit_id)
            if not property_visit:
                return {"success": False, "error": f"Property visit {task.visit_id} not found"}
            
            # Check if we have the listing agent information
            if not property_visit.sellside_agent_id:
                return {"success": False, "error": "No listing agent found for property"}
            
            # Send notification to listing agent (simulated here)
            notification_result = await self._send_notification_to_agent(
                agent_id=property_visit.sellside_agent_id,
                agent_name=property_visit.sellside_agent_name,
                property_address=property_visit.address,
                feedback_text=feedback.processed_feedback,
                feedback_timestamp=feedback.timestamp
            )
            
            # Sync to CRM if requested
            crm_result = None
            if sync_to_crm:
                crm_result = await self.sync_feedback_to_crm(
                    property_id=property_visit.property_id,
                    tour_id=property_visit.tour_id,
                    feedback=feedback.processed_feedback,
                    timestamp=feedback.timestamp
                )
            
            # Update feedback record to mark as sent
            await self.db.update_feedback_sent_status(feedback_id, True)
            
            return {
                "success": True, 
                "notification_result": notification_result,
                "crm_result": crm_result
            }
            
        except Exception as e:
            logger.error(f"Error notifying listing agent: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def _send_notification_to_agent(self, 
                                         agent_id: str, 
                                         agent_name: str,
                                         property_address: str,
                                         feedback_text: str,
                                         feedback_timestamp: str) -> Dict[str, Any]:
        """
        Send a notification to a listing agent (simulated)
        
        Args:
            agent_id: ID of the listing agent
            agent_name: Name of the listing agent
            property_address: Address of the property
            feedback_text: Text of the feedback
            feedback_timestamp: Timestamp of the feedback
            
        Returns:
            Dict: Notification result
        """
        # In a real implementation, this would send an email, SMS, or push notification
        # For now, we'll just log it
        logger.info(f"Notification sent to agent {agent_name} ({agent_id}) for property {property_address}")
        logger.info(f"Feedback: {feedback_text}")
        
        # Simulate a delay for the notification delivery
        await asyncio.sleep(0.1)
        
        return {
            "sent_to": agent_id,
            "method": "email",  # Simulated method
            "timestamp": datetime.utcnow().isoformat()
        }
    
    async def sync_feedback_to_crm(self,
                                  property_id: str,
                                  tour_id: str,
                                  feedback: str,
                                  timestamp: Optional[str] = None,
                                  buyer_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Sync feedback to CRM systems via Rollout
        
        Args:
            property_id: ID of the property
            tour_id: ID of the tour
            feedback: Feedback text
            timestamp: Timestamp of the feedback (optional)
            buyer_id: ID of the buyer (optional)
            
        Returns:
            Dict: CRM sync result with success status
        """
        max_attempts = 3
        retry_delay = 2  # seconds

        try:
            for attempt in range(max_attempts):
                try:
                    # Use the Rollout client to sync feedback to CRM systems
                    result = await rollout_client.sync_feedback(
                        property_id=property_id,
                        tour_id=tour_id,
                        feedback=feedback,
                        buyer_id=buyer_id,
                        timestamp=timestamp,
                        crm_type="all"  # Sync to all configured CRMs
                    )
                    
                    # Successful sync
                    logger.info(f"Feedback for property {property_id} synced to CRM systems")
                    return {"success": True, "result": result}
                    
                except RolloutRateLimitError as e:
                    # Rate limit errors need longer backoff
                    logger.warning(f"Rate limit reached syncing feedback (attempt {attempt+1}/{max_attempts}): {str(e)}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(retry_delay * (attempt + 2))  # Increasing delay
                    else:
                        raise
                        
                except RolloutServerError as e:
                    # Server errors may resolve with retries
                    logger.warning(f"Server error syncing feedback (attempt {attempt+1}/{max_attempts}): {str(e)}")
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(retry_delay)
                    else:
                        raise
                        
                except RolloutError as e:
                    # Handle circuit breaker open errors specifically
                    if isinstance(e, RolloutCircuitOpenError):
                        logger.error(f"Circuit breaker open when syncing feedback: {str(e)}")
                        
                        # Register failed operation for dashboard
                        op_id = str(uuid.uuid4())
                        failed_op = FailedOperation(
                            id=op_id,
                            operation=f"Feedback Sync - Property {property_id}",
                            type="feedback-sync",
                            status="FAILED",
                            last_attempt=datetime.utcnow(),
                            retry_count=attempt,
                            error=f"Circuit Breaker Open: {str(e)}",
                            data={"property_id": property_id, "tour_id": tour_id, "entity_id": property_id}
                        )
                        failed_operations[op_id] = failed_op
                        
                        # For circuit breaker, we return immediately - retrying won't help
                        # until the circuit closes again
                        return {"success": False, "error": str(e), "circuit_open": True}
                    
                    # Other API errors - less likely to resolve with retries
                    logger.error(f"Error syncing feedback to CRM: {str(e)}")
                    
                    # Register the failure for alerting if this is the last attempt
                    if attempt == max_attempts - 1:
                        alert_manager.record_operation_failure(
                            entity_id=property_id,
                            entity_type="feedback", 
                            operation_type="sync_feedback", 
                            error=str(e),
                            operation_id=f"feedback-{property_id}-{datetime.utcnow().isoformat()}",
                            details={"property_id": property_id, "tour_id": tour_id}
                        )
                    
                    raise
            
        except Exception as e:
            logger.error(f"Error syncing feedback to CRM: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def sync_tour_to_crm(self,
                              tour_id: str,
                              agent_id: str,
                              properties: List[Dict]) -> Dict[str, Any]:
        """
        Sync tour schedule to CRM systems via Rollout
        
        Sends tour schedule data to CRM systems with retry logic for failures.
        
        Args:
            tour_id: ID of the tour
            agent_id: ID of the agent
            properties: List of property details
         
        # Enhanced with retry functionality   
        Returns:
            Dict: CRM sync result
        """
        op_id = str(uuid.uuid4())
        try:
            # Use the Rollout client to sync tour to CRM systems
            result = await rollout_client.sync_tour(
                tour_id=tour_id,
                agent_id=agent_id,
                properties=properties,
                crm_type="all"  # Sync to all configured CRMs
            )

            # Store sync record in database if available
            try:
                if hasattr(self.db, 'record_crm_sync'):
                    await self.db.record_crm_sync(
                        entity_type="tour", 
                        entity_id=tour_id,
                        sync_result=result
                    )
            except Exception as db_err:
                # Non-critical failure, log but don't fail the operation
                logger.warning(f"Failed to record sync in database: {str(db_err)}")
            
            logger.info(f"Tour {tour_id} synced to CRM systems")
            return {"success": True, "result": result}
            
        except RolloutCircuitOpenError as e:
            # Handle circuit breaker specific error
            logger.error(f"Circuit breaker open when syncing tour {tour_id} to CRM: {str(e)}")
            
            # Register failed operation for dashboard
            failed_op = FailedOperation(
                id=op_id,
                operation=f"Tour Sync - Tour {tour_id}",
                type="tour-sync",
                status="FAILED",
                last_attempt=datetime.utcnow(),
                retry_count=0,
                error=f"Circuit Breaker Open: {str(e)}",
                data={"tour_id": tour_id, "agent_id": agent_id, "entity_id": tour_id}
            )
            failed_operations[op_id] = failed_op
            
            # Alert on circuit breaker failure
            alert_manager.record_operation_failure(
                entity_id=tour_id,
                entity_type="tour", 
                operation_type="sync_tour", 
                error=str(e),
                operation_id=op_id,
                details={"tour_id": tour_id, "agent_id": agent_id}
            )
            
            return {
                "success": False,
                "error": str(e),
                "tour_id": tour_id,
                "circuit_open": True,
                "retry_scheduled": False,
                "message": "Integration service unavailable due to repeated failures. The system will automatically try again when stability improves."
            }
            
        except RolloutRateLimitError as e:
            # Handle rate limit specifically
            logger.error(f"Rate limit exceeded syncing tour to CRM: {str(e)}")
            
            # Schedule retry after rate limit resets
            asyncio.create_task(self._retry_tour_sync(
                tour_id=tour_id,
                agent_id=agent_id,
                properties=properties,
                delay=65  # Rate limit typically resets after 60 seconds
            ))
            
            # Register failed operation for dashboard
            failed_op = FailedOperation(
                id=op_id,
                operation=f"Tour Sync - Tour {tour_id}",
                type="tour-sync",
                status="PENDING_RETRY",
                last_attempt=datetime.utcnow(),
                retry_count=1,
                error=f"Rate Limit Exceeded: {str(e)}",
                data={"tour_id": tour_id, "agent_id": agent_id, "entity_id": tour_id}
            )
            failed_operations[op_id] = failed_op
            
            # Alert on rate limit failure if needed
            alert_manager.record_operation_failure(
                entity_id=tour_id,
                entity_type="tour", 
                operation_type="sync_tour", 
                error=str(e),
                operation_id=op_id)
            
            return {
                "success": False, 
                "error": str(e),
                "retry_scheduled": True,
                "retry_after": "~1 minute"
            }
            
        except Exception as e:
            logger.error(f"Error syncing tour to CRM: {str(e)}")
            
            # Register failed operation for dashboard
            failed_op = FailedOperation(
                id=op_id,
                operation=f"Tour Sync - Tour {tour_id}",
                type="tour-sync",
                status="FAILED",
                last_attempt=datetime.utcnow(),
                retry_count=0,
                error=str(e),
                data={"tour_id": tour_id, "agent_id": agent_id, "entity_id": tour_id}
            )
            failed_operations[op_id] = failed_op
            
            # Alert on general failure
            alert_manager.record_operation_failure(
                entity_id=tour_id,
                entity_type="tour",
                operation_type="sync_tour",
                error=str(e),
                operation_id=op_id)
                
            return {"success": False, "error": str(e)}
    
    async def process_unsent_feedback(self) -> Dict[str, Any]:
        """
        Process all unsent feedback notifications
        
        Returns:
            Dict: Processing result
        """
        try:
            # Get all feedback that hasn't been sent to agents
            unsent_feedback = await self.db.get_unsent_feedback()
            
            # Process each unsent feedback
            results = []
            for feedback in unsent_feedback:
                result = await self.notify_listing_agent(feedback.id)
                results.append({
                    "feedback_id": feedback.id,
                    "result": result
                })
            
            return {
                "success": True,
                "processed_count": len(unsent_feedback),
                "results": results
            }
            
        except Exception as e:
            logger.error(f"Error processing unsent feedback: {str(e)}")
            return {"success": False, "error": str(e)}
            
    async def _retry_tour_sync(self, tour_id: str, agent_id: str, 
                              properties: List[Dict], delay: int = 60) -> None:
        """
        Internal helper to retry tour sync after a delay
        
        Args:
            tour_id: ID of the tour
            agent_id: ID of the agent
            properties: List of property details
            delay: Seconds to wait before retrying
        """
        try:
            # Wait for specified delay
            logger.info(f"Scheduling tour sync retry in {delay} seconds for tour {tour_id}")
            await asyncio.sleep(delay)
            
            # Attempt the sync again
            result = await rollout_client.sync_tour(
                tour_id=tour_id,
                agent_id=agent_id,
                properties=properties,
                crm_type="all"
            )
            
            logger.info(f"Retry successful: Tour {tour_id} synced to CRM systems")
            
            # Find any existing failed operations for this tour and mark as resolved
            for op_id, op in list(failed_operations.items()):
                if op.type == "tour-sync" and op.data.get("tour_id") == tour_id:
                    failed_operations[op_id].status = "RESOLVED"
            
        except Exception as e:
            logger.error(f"Retry failed for tour {tour_id} sync: {str(e)}")
            
            # Register the retry failure
            op_id = str(uuid.uuid4())
            failed_op = FailedOperation(
                id=op_id,
                operation=f"Tour Sync Retry - Tour {tour_id}",
                type="tour-sync",
                status="FAILED",
                last_attempt=datetime.utcnow(),
                retry_count=1,  # This is already a retry
                error=f"Retry Failed: {str(e)}",
                data={"tour_id": tour_id, "agent_id": agent_id, "entity_id": tour_id}
            )
            failed_operations[op_id] = failed_op
            # No further retries to avoid infinite loops
