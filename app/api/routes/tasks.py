from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import datetime
import logging

from app.models import (
    Task, TaskCreate, TaskUpdate, TaskType, TaskStatus,
    create_task, get_task, update_task, update_task_status,
    get_tasks_by_visit, get_tasks_by_type, get_pending_tasks
)
from app.services import trigger_feedback_collection

router = APIRouter(prefix="/tasks", tags=["tasks"])

@router.get("/", response_model=List[Dict[str, Any]])
async def get_tasks(
    visit_id: Optional[str] = None,
    task_type: Optional[str] = None,
    pending_only: bool = False
):
    """
    Get tasks, optionally filtered by visit ID, task type, or pending status.
    """
    if visit_id:
        tasks = get_tasks_by_visit(visit_id)
    elif task_type:
        tasks = get_tasks_by_type(task_type)
    elif pending_only:
        tasks = get_pending_tasks()
    else:
        # Get all tasks (not implemented yet)
        tasks = []
    
    # Format the response
    result = []
    for task in tasks:
        task_data = {
            "task_id": task.id,
            "visit_id": task.visit_id,
            "task_type": task.task_type,
            "status": task.status,
            "scheduled_time": task.scheduled_time,
            "completed_time": task.completed_time,
            "shipment_id": task.shipment_id
        }
        result.append(task_data)
    
    return result

@router.get("/{task_id}", response_model=Dict[str, Any])
async def get_task_details(task_id: str):
    """
    Get details of a specific task.
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Get property visit
    from app.models import get_property_visit
    property_visit = get_property_visit(task.visit_id)
    
    # Format the response
    result = {
        "task_id": task.id,
        "visit_id": task.visit_id,
        "property_address": property_visit.address if property_visit else None,
        "task_type": task.task_type,
        "status": task.status,
        "scheduled_time": task.scheduled_time,
        "completed_time": task.completed_time,
        "shipment_id": task.shipment_id
    }
    
    # Add feedback for feedback collection tasks
    if task.task_type == "feedback_collection":
        from app.models import get_feedback_by_task
        feedback_entries = get_feedback_by_task(task.id)
        
        result["feedback"] = []
        for feedback in feedback_entries:
            feedback_data = {
                "feedback_id": feedback.id,
                "source": feedback.feedback_source,
                "raw_feedback": feedback.raw_feedback,
                "processed_feedback": feedback.processed_feedback,
                "timestamp": feedback.timestamp,
                "sent_to_agent": feedback.sent_to_agent
            }
            result["feedback"].append(feedback_data)
    
    return result

@router.put("/{task_id}/status", response_model=Dict[str, Any])
async def update_status(task_id: str, status: str, timestamp: Optional[str] = None):
    """
    Update the status of a task.
    """
    valid_statuses = [s for s in TaskStatus.__members__.values()]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Use the current timestamp if not provided
    if not timestamp:
        timestamp = datetime.datetime.now().isoformat()
    
    # Update the task status
    updated_task = update_task_status(task_id, status, timestamp)
    
    # If a property tour task is completed, trigger feedback collection
    if task.task_type == TaskType.PROPERTY_TOUR and status == TaskStatus.COMPLETED:
        # Trigger feedback collection asynchronously
        feedback_result = await trigger_feedback_collection(task_id)
        
        return {
            "task_id": updated_task.id,
            "status": updated_task.status,
            "feedback_collection": feedback_result
        }
    
    return {
        "task_id": updated_task.id,
        "status": updated_task.status
    }

@router.put("/{task_id}", response_model=Dict[str, Any])
async def update_task_details(task_id: str, update_data: TaskUpdate):
    """
    Update details of a task.
    """
    task = get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    # Convert the update data to a dictionary
    update_dict = update_data.dict(exclude_unset=True)
    
    # Update the task
    updated_task = update_task(task_id, update_dict)
    
    return {
        "task_id": updated_task.id,
        "visit_id": updated_task.visit_id,
        "task_type": updated_task.task_type,
        "status": updated_task.status,
        "scheduled_time": updated_task.scheduled_time,
        "completed_time": updated_task.completed_time,
        "shipment_id": updated_task.shipment_id
    }

@router.post("/property-tour", response_model=Dict[str, Any])
async def create_property_tour_task(visit_id: str, scheduled_time: str):
    """
    Create a property tour task.
    """
    from app.models import create_property_tour_task
    
    task = create_property_tour_task(visit_id, scheduled_time)
    
    return {
        "task_id": task.id,
        "visit_id": task.visit_id,
        "task_type": task.task_type,
        "status": task.status,
        "scheduled_time": task.scheduled_time
    }

@router.post("/feedback", response_model=Dict[str, Any])
async def create_feedback_task(visit_id: str, scheduled_time: str):
    """
    Create a feedback collection task.
    """
    from app.models import create_feedback_task
    
    task = create_feedback_task(visit_id, scheduled_time)
    
    return {
        "task_id": task.id,
        "visit_id": task.visit_id,
        "task_type": task.task_type,
        "status": task.status,
        "scheduled_time": task.scheduled_time
    }
