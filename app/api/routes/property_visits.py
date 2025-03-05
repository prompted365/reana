from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import datetime
import logging

from app.models import (
    PropertyVisit, PropertyVisitCreate, create_property_visit, get_property_visit,
    update_property_visit, get_property_visits_by_tour, record_arrival, record_departure,
    get_next_property_visit, get_current_property_visit
)

router = APIRouter(prefix="/property-visits", tags=["property-visits"])

@router.get("/", response_model=List[Dict[str, Any]])
async def get_property_visits(tour_id: str):
    """
    Get all property visits for a tour.
    """
    visits = get_property_visits_by_tour(tour_id)
    
    # Format the response
    result = []
    for visit in visits:
        visit_data = {
            "visit_id": visit.id,
            "tour_id": visit.tour_id,
            "address": visit.address,
            "property_id": visit.property_id,
            "scheduled_arrival": visit.scheduled_arrival,
            "scheduled_departure": visit.scheduled_departure,
            "actual_arrival": visit.actual_arrival,
            "actual_departure": visit.actual_departure,
            "status": visit.status,
            "sellside_agent_name": visit.sellside_agent_name,
            "contact_method": visit.contact_method,
            "confirmation_status": visit.confirmation_status,
            "constraint_indicator": visit.constraint_indicator,
            "square_footage": visit.square_footage,
            "video_url": visit.video_url
        }
        result.append(visit_data)
    
    return result

@router.get("/{visit_id}", response_model=Dict[str, Any])
async def get_property_visit_details(visit_id: str):
    """
    Get details of a specific property visit.
    """
    visit = get_property_visit(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Property visit not found")
    
    # Get tasks for this visit
    from app.models import get_tasks_by_visit
    tasks = get_tasks_by_visit(visit.id)
    
    # Format the response
    result = {
        "visit_id": visit.id,
        "tour_id": visit.tour_id,
        "address": visit.address,
        "property_id": visit.property_id,
        "scheduled_arrival": visit.scheduled_arrival,
        "scheduled_departure": visit.scheduled_departure,
        "actual_arrival": visit.actual_arrival,
        "actual_departure": visit.actual_departure,
        "status": visit.status,
        "sellside_agent_name": visit.sellside_agent_name,
        "contact_method": visit.contact_method,
        "confirmation_status": visit.confirmation_status,
        "constraint_indicator": visit.constraint_indicator,
        "square_footage": visit.square_footage,
        "video_url": visit.video_url,
        "tasks": []
    }
    
    # Add tasks
    for task in tasks:
        task_data = {
            "task_id": task.id,
            "task_type": task.task_type,
            "status": task.status,
            "scheduled_time": task.scheduled_time,
            "completed_time": task.completed_time
        }
        
        # Add feedback for feedback collection tasks
        if task.task_type == "feedback_collection":
            from app.models import get_feedback_by_task
            feedback_entries = get_feedback_by_task(task.id)
            
            task_data["feedback"] = []
            for feedback in feedback_entries:
                feedback_data = {
                    "feedback_id": feedback.id,
                    "source": feedback.feedback_source,
                    "raw_feedback": feedback.raw_feedback,
                    "processed_feedback": feedback.processed_feedback,
                    "timestamp": feedback.timestamp,
                    "sent_to_agent": feedback.sent_to_agent
                }
                task_data["feedback"].append(feedback_data)
        
        result["tasks"].append(task_data)
    
    return result

@router.post("/", response_model=Dict[str, Any])
async def create_new_property_visit(visit: PropertyVisitCreate):
    """
    Create a new property visit.
    """
    created_visit = create_property_visit(visit)
    
    return {
        "visit_id": created_visit.id,
        "tour_id": created_visit.tour_id,
        "address": created_visit.address,
        "property_id": created_visit.property_id,
        "scheduled_arrival": created_visit.scheduled_arrival,
        "scheduled_departure": created_visit.scheduled_departure,
        "status": created_visit.status
    }

@router.put("/{visit_id}/arrival", response_model=Dict[str, Any])
async def record_property_arrival(visit_id: str, arrival_time: Optional[str] = None):
    """
    Record the actual arrival time at a property.
    """
    # Use the current timestamp if not provided
    if not arrival_time:
        arrival_time = datetime.datetime.now().isoformat()
    
    updated_visit = record_arrival(visit_id, arrival_time)
    if not updated_visit:
        raise HTTPException(status_code=404, detail="Property visit not found")
    
    # Update the property tour task status
    from app.models import get_tasks_by_visit, update_task_status, TaskType, TaskStatus
    tasks = get_tasks_by_visit(visit_id)
    for task in tasks:
        if task.task_type == TaskType.PROPERTY_TOUR:
            update_task_status(task.id, TaskStatus.IN_PROGRESS)
    
    return {
        "visit_id": updated_visit.id,
        "address": updated_visit.address,
        "actual_arrival": updated_visit.actual_arrival,
        "status": updated_visit.status
    }

@router.put("/{visit_id}/departure", response_model=Dict[str, Any])
async def record_property_departure(visit_id: str, departure_time: Optional[str] = None):
    """
    Record the actual departure time from a property.
    """
    # Use the current timestamp if not provided
    if not departure_time:
        departure_time = datetime.datetime.now().isoformat()
    
    updated_visit = record_departure(visit_id, departure_time)
    if not updated_visit:
        raise HTTPException(status_code=404, detail="Property visit not found")
    
    # Update the property tour task status
    from app.models import get_tasks_by_visit, update_task_status, TaskType, TaskStatus
    tasks = get_tasks_by_visit(visit_id)
    for task in tasks:
        if task.task_type == TaskType.PROPERTY_TOUR:
            update_task_status(task.id, TaskStatus.COMPLETED)
    
    # Trigger feedback collection
    from app.services import trigger_feedback_collection
    for task in tasks:
        if task.task_type == TaskType.PROPERTY_TOUR:
            await trigger_feedback_collection(task.id)
    
    return {
        "visit_id": updated_visit.id,
        "address": updated_visit.address,
        "actual_departure": updated_visit.actual_departure,
        "status": updated_visit.status
    }

@router.put("/{visit_id}/status", response_model=Dict[str, Any])
async def update_property_visit_status(visit_id: str, status: str):
    """
    Update the status of a property visit.
    """
    valid_statuses = ["scheduled", "arrived", "completed", "cancelled", "skipped"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    visit = get_property_visit(visit_id)
    if not visit:
        raise HTTPException(status_code=404, detail="Property visit not found")
    
    updated_visit = update_property_visit(visit_id, {"status": status})
    
    return {
        "visit_id": updated_visit.id,
        "address": updated_visit.address,
        "status": updated_visit.status
    }

@router.get("/tour/{tour_id}/next", response_model=Dict[str, Any])
async def get_next_visit(tour_id: str):
    """
    Get the next scheduled property visit for a tour.
    """
    visit = get_next_property_visit(tour_id)
    if not visit:
        raise HTTPException(status_code=404, detail="No next property visit found")
    
    return {
        "visit_id": visit.id,
        "tour_id": visit.tour_id,
        "address": visit.address,
        "scheduled_arrival": visit.scheduled_arrival,
        "scheduled_departure": visit.scheduled_departure,
        "status": visit.status
    }

@router.get("/tour/{tour_id}/current", response_model=Dict[str, Any])
async def get_current_visit(tour_id: str):
    """
    Get the current property visit (status = 'arrived') for a tour.
    """
    visit = get_current_property_visit(tour_id)
    if not visit:
        raise HTTPException(status_code=404, detail="No current property visit found")
    
    return {
        "visit_id": visit.id,
        "tour_id": visit.tour_id,
        "address": visit.address,
        "scheduled_arrival": visit.scheduled_arrival,
        "scheduled_departure": visit.scheduled_departure,
        "actual_arrival": visit.actual_arrival,
        "status": visit.status
    }
