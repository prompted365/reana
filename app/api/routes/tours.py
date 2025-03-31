"""
Tour Routes

This module provides API routes for managing real estate tours.
"""

import logging
from typing import List, Dict, Optional, Any
import time
from fastapi import APIRouter, HTTPException, Depends, Query, Body
from fastapi.responses import JSONResponse

from ...models.database import get_db, get_db_connection
from ...models.tour import Tour, TourCreate, TourResponse, TourStatus
from ...services.optimization_service import OptimizationService
from ...services.notification_service import NotificationService 
from ...services.rollout_client import (rollout_client, RolloutError, RolloutRateLimitError, 
                                     RolloutServerError, RolloutCircuitOpenError)

# Configure logging
logger = logging.getLogger(__name__)

# Create API router
router = APIRouter(prefix="/tours", tags=["tours"])


@router.post("/", response_model=TourResponse)
async def create_tour(
    tour_data: TourCreate,
    db = Depends(get_db),
    sync_to_crm: bool = Query(True, description="Whether to sync tour to CRM systems")
):
    """
    Create a new real estate tour and optimize the route
    
    Args:
        tour_data: Tour creation data
        db: Database dependency
        sync_to_crm: Whether to sync tour to CRM systems
        
    Returns:
        TourResponse: Created tour data
    """
    try:
        # Create optimization service
        optimization_service = OptimizationService(db)
        
        # Create tour and optimize route
        tour = await optimization_service.create_and_optimize_tour(
            agent_id=tour_data.agent_id,
            property_addresses=tour_data.property_addresses,
            start_time=tour_data.start_time,
            strategy=tour_data.strategy
        )
        
        # Sync to CRM if requested
        if sync_to_crm:
            sync_result = await sync_tour_to_crm(tour, db)
            
            # If sync failed but it's a recoverable error, don't fail the tour creation
            if not sync_result.get("success", False):
                if sync_result.get("retry_scheduled", False):
                    logger.warning(f"Tour created successfully but CRM sync scheduled for retry: {sync_result.get('error')}")
                    # Append sync status to response
                    tour.sync_status = "RETRY_SCHEDULED"
                    tour.sync_message = "CRM sync scheduled for retry due to rate limiting"
                else:
                    logger.error(f"Tour created successfully but CRM sync failed: {sync_result.get('error')}")
                    tour.sync_status = "FAILED"
        
        return tour
    except Exception as e:
        logger.error(f"Error creating tour: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tour_id}", response_model=TourResponse)
async def get_tour(tour_id: str, db = Depends(get_db)):
    """
    Get a specific tour by ID
    
    Args:
        tour_id: Tour ID
        db: Database dependency
        
    Returns:
        TourResponse: Tour data
    """
    tour = await db.get_tour(tour_id)
    if not tour:
        raise HTTPException(status_code=404, detail=f"Tour {tour_id} not found")
    return tour


@router.put("/{tour_id}/status", response_model=TourResponse)
async def update_tour_status(
    tour_id: str,
    status: TourStatus,
    db = Depends(get_db),
    sync_to_crm: bool = Query(True, description="Whether to sync status update to CRM systems")
):
    """
    Update the status of a tour
    
    Args:
        tour_id: Tour ID
        status: New tour status
        db: Database dependency
        sync_to_crm: Whether to sync status update to CRM systems
        
    Returns:
        TourResponse: Updated tour data
    """
    # Update status in database
    tour = await db.update_tour_status(tour_id, status)
    if not tour:
        raise HTTPException(status_code=404, detail=f"Tour {tour_id} not found")
    
    # Sync to CRM if requested
    if sync_to_crm:
        await sync_tour_to_crm(tour, db)
    
    return tour


@router.get("/", response_model=List[TourResponse])
async def get_tours(
    agent_id: Optional[str] = None,
    status: Optional[TourStatus] = None,
    limit: int = 10,
    db = Depends(get_db)
):
    """
    Get tours, optionally filtered by agent ID and status
    
    Args:
        agent_id: Filter by agent ID (optional)
        status: Filter by tour status (optional)
        limit: Maximum number of tours to return
        db: Database dependency
        
    Returns:
        List[TourResponse]: List of tours
    """
    tours = await db.get_tours(agent_id=agent_id, status=status, limit=limit)
    return tours


@router.post("/{tour_id}/sync-to-crm", response_model=Dict[str, Any])
async def manually_sync_tour_to_crm(
    tour_id: str,
    db = Depends(get_db)
):
    """
    Manually sync a tour to CRM systems
    
    Args:
        tour_id: Tour ID
        db: Database dependency
        
    Returns:
        Dict: Sync result
    """
    tour = await db.get_tour(tour_id)
    if not tour:
        raise HTTPException(status_code=404, detail=f"Tour {tour_id} not found")
    
    result = await sync_tour_to_crm(tour, db)
    return {"success": True, "result": result}
    

@router.get("/{tour_id}/sync-status", response_model=Dict[str, Any])
async def get_tour_sync_status(
    tour_id: str,
    db = Depends(get_db)
):
    """Get the CRM sync status for a tour"""
    tour = await db.get_tour(tour_id)
    if not tour:
        raise HTTPException(status_code=404, detail=f"Tour {tour_id} not found")
        
    return {"tour_id": tour_id, "sync_status": getattr(tour, "sync_status", "UNKNOWN")}


# Helper function to sync tour to CRM systems
async def sync_tour_to_crm(tour: Tour, db) -> Dict[str, Any]:
    """
    Sync a tour to CRM systems
    
    Args:
        tour: Tour data
        db: Database instance
        
    Returns:
        Dict: Sync result
    """
    try:
        start_time = time.time()
        
        # Get property visits for the tour
        logger.info(f"Syncing tour {tour.id} to CRM systems")
        
        property_visits = await db.get_property_visits_for_tour(tour.id)
        
        # Format properties for CRM sync
        properties = []
        for visit in property_visits:
            properties.append({
                "address": visit.address,
                "visitTime": visit.scheduled_arrival,
                "propertyId": visit.property_id
            })
            
        # Handle edge case of no properties
        if not properties:
            logger.warning(f"No properties found for tour {tour.id}, cannot sync to CRM")
            return {
                "success": False, 
                "error": "No properties found for tour",
                "tour_id": tour.id,
                "properties_count": 0,
                "duration_ms": int((time.time() - start_time) * 1000),
                "timestamp": time.time()
            }

        
        # Create notification service
        notification_service = NotificationService(db)
        
        # Sync tour to CRM systems
        result = await notification_service.sync_tour_to_crm(
            tour_id=tour.id,
            agent_id=tour.agent_id,
            properties=properties
        )
        
        # Add monitoring information
        result["tour_id"] = tour.id
        result["properties_count"] = len(properties)
        result["duration_ms"] = int((time.time() - start_time) * 1000)
        result["timestamp"] = time.time()
        
        # Update tour sync status in database if possible
        try:
            if hasattr(db, 'update_tour_sync_status'):
                await db.update_tour_sync_status(
                    tour_id=tour.id,
                    sync_status="SUCCESS" if result.get("success", False) else "FAILED",
                    sync_details=result
                )
        except Exception as db_err:
            logger.warning(f"Failed to update tour sync status: {str(db_err)}")
        
        return result
    
    except RolloutCircuitOpenError as e:
        # Handle circuit breaker open state specifically
        logger.error(f"Circuit breaker open when syncing tour {tour.id} to CRM: {str(e)}")
        
        # Try to update tour sync status
        try:
            if hasattr(db, 'update_tour_sync_status'):
                await db.update_tour_sync_status(
                    tour_id=tour.id,
                    sync_status="UNAVAILABLE",
                    sync_details={"error": str(e), "circuit_open": True}
                )
        except Exception as db_err:
            logger.warning(f"Failed to update tour sync status: {str(db_err)}")
            
        return {
            "success": False,
            "error": f"CRM integration service temporarily unavailable: {str(e)}",
            "tour_id": tour.id,
            "circuit_open": True
        }
            
    except RolloutRateLimitError as e:
        # Handle rate limit specifically
        logger.error(f"Rate limit exceeded syncing tour {tour.id} to CRM: {str(e)}")
        
        # Try to update tour sync status
        try:
            if hasattr(db, 'update_tour_sync_status'):
                await db.update_tour_sync_status(
                    tour_id=tour.id,
                    sync_status="RETRY_SCHEDULED",
                    sync_details={"error": str(e), "retry_after": "60 seconds"}
                )
        except Exception as db_err:
            logger.warning(f"Failed to update tour sync status: {str(db_err)}")
            
        # Return detailed error for client
        result = {
            "success": False,
            "error": f"Rate limit exceeded: {str(e)}",
            "tour_id": tour.id,
            "retry_scheduled": True,
            "retry_after": "~1 minute"
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Error syncing tour {tour.id} to CRM: {str(e)}", exc_info=True)
        return {"success": False, "error": str(e)}


@router.get("/{tour_id}/journal", response_model=Dict[str, Any])
async def get_tour_journal(tour_id: str, db = Depends(get_db)):
    """
    Get a chronological journal of a tour, including property visits and feedback
    
    Args:
        tour_id: Tour ID
        db: Database dependency
        
    Returns:
        Dict: Tour journal data
    """
    # Check if tour exists
    tour = await db.get_tour(tour_id)
    if not tour:
        raise HTTPException(status_code=404, detail=f"Tour {tour_id} not found")
    
    # Get property visits for the tour
    property_visits = await db.get_property_visits_for_tour(tour_id)
    
    # Build the journal
    journal_entries = []
    
    # Add tour creation entry
    journal_entries.append({
        "type": "tour_created",
        "timestamp": tour.created_at,
        "data": {
            "tour_id": tour.id,
            "agent_id": tour.agent_id,
            "status": tour.status
        }
    })
    
    # Add entries for each property visit
    for visit in property_visits:
        # Add scheduled visit entry
        journal_entries.append({
            "type": "visit_scheduled",
            "timestamp": visit.scheduled_arrival,
            "data": {
                "visit_id": visit.id,
                "address": visit.address,
                "property_id": visit.property_id,
                "scheduled_arrival": visit.scheduled_arrival,
                "scheduled_departure": visit.scheduled_departure
            }
        })
        
        # Add actual visit entries if available
        if visit.actual_arrival:
            journal_entries.append({
                "type": "visit_arrived",
                "timestamp": visit.actual_arrival,
                "data": {
                    "visit_id": visit.id,
                    "address": visit.address,
                    "property_id": visit.property_id,
                    "actual_arrival": visit.actual_arrival
                }
            })
        
        if visit.actual_departure:
            journal_entries.append({
                "type": "visit_departed",
                "timestamp": visit.actual_departure,
                "data": {
                    "visit_id": visit.id,
                    "address": visit.address,
                    "property_id": visit.property_id,
                    "actual_departure": visit.actual_departure
                }
            })
        
        # Get tasks for the visit
        tasks = await db.get_tasks_by_visit(visit.id)
        
        # Add entries for tasks
        for task in tasks:
            journal_entries.append({
                "type": f"task_{task.status.lower()}",
                "timestamp": task.updated_at or task.created_at,
                "data": {
                    "task_id": task.id,
                    "visit_id": visit.id,
                    "task_type": task.task_type,
                    "status": task.status
                }
            })
            
            # If it's a feedback task, get the feedback
            if task.task_type == "FEEDBACK" and task.status == "COMPLETED":
                feedback_list = await db.get_feedback_by_task(task.id)
                
                # Add entries for feedback
                for feedback in feedback_list:
                    journal_entries.append({
                        "type": "feedback_received",
                        "timestamp": feedback.timestamp,
                        "data": {
                            "feedback_id": feedback.id,
                            "task_id": task.id,
                            "visit_id": visit.id,
                            "property_id": visit.property_id,
                            "raw_feedback": feedback.raw_feedback,
                            "processed_feedback": feedback.processed_feedback,
                            "sent_to_agent": feedback.sent_to_agent
                        }
                    })
    
    # Sort journal entries by timestamp
    journal_entries.sort(key=lambda entry: entry["timestamp"])
    
    return {
        "tour_id": tour_id,
        "agent_id": tour.agent_id,
        "start_time": tour.start_time,
        "end_time": tour.end_time,
        "status": tour.status,
        "journal": journal_entries
    }
