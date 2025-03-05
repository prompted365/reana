from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import datetime
import logging

from app.models import (
    Feedback, FeedbackCreate, FeedbackUpdate, FeedbackSource,
    create_feedback, get_feedback, update_feedback, get_feedback_by_task,
    get_unsent_feedback, mark_feedback_as_sent, add_processed_feedback,
    create_sms_feedback, create_voice_feedback
)
from app.services import (
    process_feedback, summarize_feedback_with_ai, send_feedback_notification
)

router = APIRouter(prefix="/feedback", tags=["feedback"])

@router.get("/", response_model=List[Dict[str, Any]])
async def get_feedback_entries(
    task_id: Optional[str] = None,
    unsent_only: bool = False
):
    """
    Get feedback entries, optionally filtered by task ID or unsent status.
    """
    if task_id:
        feedback_entries = get_feedback_by_task(task_id)
    elif unsent_only:
        feedback_entries = get_unsent_feedback()
    else:
        # Get all feedback (not implemented yet)
        feedback_entries = []
    
    # Format the response
    result = []
    for feedback in feedback_entries:
        feedback_data = {
            "feedback_id": feedback.id,
            "task_id": feedback.task_id,
            "raw_feedback": feedback.raw_feedback,
            "processed_feedback": feedback.processed_feedback,
            "feedback_source": feedback.feedback_source,
            "timestamp": feedback.timestamp,
            "sent_to_agent": feedback.sent_to_agent
        }
        result.append(feedback_data)
    
    return result

@router.get("/{feedback_id}", response_model=Dict[str, Any])
async def get_feedback_details(feedback_id: str):
    """
    Get details of a specific feedback entry.
    """
    feedback = get_feedback(feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Get task and property visit
    from app.models import get_task, get_property_visit
    task = get_task(feedback.task_id)
    property_visit = get_property_visit(task.visit_id) if task else None
    
    # Format the response
    result = {
        "feedback_id": feedback.id,
        "task_id": feedback.task_id,
        "task_type": task.task_type if task else None,
        "property_address": property_visit.address if property_visit else None,
        "raw_feedback": feedback.raw_feedback,
        "processed_feedback": feedback.processed_feedback,
        "feedback_source": feedback.feedback_source,
        "timestamp": feedback.timestamp,
        "sent_to_agent": feedback.sent_to_agent
    }
    
    return result

@router.post("/sms", response_model=Dict[str, Any])
async def submit_sms_feedback(task_id: str, raw_feedback: str):
    """
    Submit feedback via SMS.
    """
    # Create the feedback entry
    feedback = create_sms_feedback(task_id, raw_feedback)
    
    # Process the feedback
    await process_feedback(feedback.id)
    
    return {
        "feedback_id": feedback.id,
        "task_id": feedback.task_id,
        "feedback_source": feedback.feedback_source,
        "timestamp": feedback.timestamp
    }

@router.post("/voice", response_model=Dict[str, Any])
async def submit_voice_feedback(task_id: str, raw_feedback: str):
    """
    Submit feedback via voice transcription.
    """
    # Create the feedback entry
    feedback = create_voice_feedback(task_id, raw_feedback)
    
    # Process the feedback
    await process_feedback(feedback.id)
    
    return {
        "feedback_id": feedback.id,
        "task_id": feedback.task_id,
        "feedback_source": feedback.feedback_source,
        "timestamp": feedback.timestamp
    }

@router.put("/{feedback_id}/process", response_model=Dict[str, Any])
async def process_feedback_entry(feedback_id: str):
    """
    Process a feedback entry using AI.
    """
    feedback = get_feedback(feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Process the feedback
    result = await process_feedback(feedback_id)
    
    return result

@router.put("/{feedback_id}/notify", response_model=Dict[str, Any])
async def notify_agent_about_feedback(feedback_id: str):
    """
    Send a notification about feedback to the listing agent.
    """
    feedback = get_feedback(feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Send the notification
    result = await send_feedback_notification(feedback_id)
    
    return result

@router.put("/{feedback_id}", response_model=Dict[str, Any])
async def update_feedback_entry(feedback_id: str, update_data: FeedbackUpdate):
    """
    Update a feedback entry.
    """
    feedback = get_feedback(feedback_id)
    if not feedback:
        raise HTTPException(status_code=404, detail="Feedback not found")
    
    # Convert the update data to a dictionary
    update_dict = update_data.dict(exclude_unset=True)
    
    # Update the feedback
    updated_feedback = update_feedback(feedback_id, update_dict)
    
    return {
        "feedback_id": updated_feedback.id,
        "task_id": updated_feedback.task_id,
        "raw_feedback": updated_feedback.raw_feedback,
        "processed_feedback": updated_feedback.processed_feedback,
        "feedback_source": updated_feedback.feedback_source,
        "timestamp": updated_feedback.timestamp,
        "sent_to_agent": updated_feedback.sent_to_agent
    }

@router.post("/process-unsent", response_model=Dict[str, Any])
async def process_all_unsent_feedback():
    """
    Process all unsent feedback and send notifications.
    """
    from app.services import process_unsent_feedback
    
    # Process unsent feedback
    result = await process_unsent_feedback()
    
    return result
