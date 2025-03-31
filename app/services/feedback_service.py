import asyncio
import datetime
import logging
from typing import Dict, Any, List, Optional

from app.models import (
    Task, TaskStatus, get_task, update_task_status,
    Feedback, FeedbackSource, create_sms_feedback, create_voice_feedback,
    add_processed_feedback, mark_feedback_as_sent, get_feedback,
    get_property_visit, get_tasks_by_visit
)
from app.utils.time_utils import current_timestamp

logging.basicConfig(level=logging.INFO)

async def trigger_feedback_collection(task_id: str) -> Dict[str, Any]:
    """
    Trigger feedback collection for a completed property tour task.
    This will initiate SMS and/or voice feedback collection based on preferences.
    """
    task = get_task(task_id)
    if not task:
        logging.error(f"Task not found: {task_id}")
        return {"error": "Task not found"}
    
    if task.task_type != "property_tour":
        logging.error(f"Task is not a property tour: {task_id}")
        return {"error": "Task is not a property tour"}
    
    if task.status != TaskStatus.COMPLETED:
        logging.error(f"Task is not completed: {task_id}")
        return {"error": "Task is not completed"}
    
    # Get the property visit
    property_visit = get_property_visit(task.visit_id)
    if not property_visit:
        logging.error(f"Property visit not found: {task.visit_id}")
        return {"error": "Property visit not found"}
    
    # Determine feedback collection methods based on preferences
    # For now, we'll use both SMS and voice
    feedback_methods = ["sms", "voice"]
    
    # Create a feedback collection task
    from app.models import create_feedback_task
    feedback_task = create_feedback_task(
        visit_id=property_visit.id,
        scheduled_time=datetime.datetime.now().isoformat()
    )
    
    # Update the feedback task status to in_progress
    update_task_status(feedback_task.id, TaskStatus.IN_PROGRESS)
    
    # Initiate feedback collection methods in parallel
    collection_tasks = []
    for method in feedback_methods:
        if method == "sms":
            collection_tasks.append(collect_sms_feedback(feedback_task.id, property_visit.id))
        elif method == "voice":
            collection_tasks.append(collect_voice_feedback(feedback_task.id, property_visit.id))
    
    # Run feedback collection methods in parallel
    await asyncio.gather(*collection_tasks)
    
    return {
        "status": "feedback_collection_initiated",
        "feedback_task_id": feedback_task.id
    }

async def collect_sms_feedback(task_id: str, visit_id: str) -> Dict[str, Any]:
    """
    Collect feedback via SMS.
    In a real implementation, this would integrate with an SMS service.
    For now, we'll simulate the process.
    """
    logging.info(f"Collecting SMS feedback for task {task_id}, visit {visit_id}")
    
    # In a real implementation, this would send an SMS and wait for a response
    # For simulation, we'll create a placeholder feedback
    simulated_feedback = "The property was nice but smaller than expected. The kitchen needs updating, but the location is excellent. The backyard is a good size for our needs."
    
    # Create a feedback entry
    feedback = create_sms_feedback(task_id, simulated_feedback)
    
    # Process the feedback
    await process_feedback(feedback.id)
    
    return {"status": "sms_feedback_collected", "feedback_id": feedback.id}

async def collect_voice_feedback(task_id: str, visit_id: str) -> Dict[str, Any]:
    """
    Collect feedback via voice call.
    In a real implementation, this would integrate with a voice service.
    For now, we'll simulate the process.
    """
    logging.info(f"Collecting voice feedback for task {task_id}, visit {visit_id}")
    
    # In a real implementation, this would initiate a voice call and transcribe the response
    # For simulation, we'll create a placeholder feedback
    simulated_feedback = "I really liked the natural light in the living room. The master bedroom was spacious, but the second bedroom was too small. The neighborhood seemed quiet and safe."
    
    # Create a feedback entry
    feedback = create_voice_feedback(task_id, simulated_feedback)
    
    # Process the feedback
    await process_feedback(feedback.id)
    
    return {"status": "voice_feedback_collected", "feedback_id": feedback.id}

async def process_feedback(feedback_id: str) -> Dict[str, Any]:
    """
    Process raw feedback using AI and prepare it for sending to the listing agent.
    """
    feedback = get_feedback(feedback_id)
    if not feedback:
        logging.error(f"Feedback not found: {feedback_id}")
        return {"error": "Feedback not found"}
    
    # In a real implementation, this would use an AI service to summarize the feedback
    # For now, we'll simulate the process
    raw_feedback = feedback.raw_feedback or ""
    
    # Simulate AI processing
    processed_feedback = await summarize_feedback_with_ai(raw_feedback)
    
    # Update the feedback with the processed summary
    add_processed_feedback(feedback_id, processed_feedback)
    
    # Notify the listing agent
    await notify_listing_agent(feedback_id)
    
    return {"status": "feedback_processed", "feedback_id": feedback_id}

async def summarize_feedback_with_ai(raw_feedback: str) -> str:
    """
    Summarize raw feedback using AI.
    In a real implementation, this would call an AI service.
    For now, we'll simulate the process.
    """
    # Simulate AI processing delay
    await asyncio.sleep(1)
    
    # Simple simulation of AI summarization
    words = raw_feedback.split()
    if len(words) <= 10:
        return raw_feedback
    
    # Extract key points (simplified simulation)
    sentences = raw_feedback.split('.')
    key_points = []
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
        
        # Look for sentiment indicators
        positive_words = ["nice", "good", "great", "excellent", "liked", "love", "spacious"]
        negative_words = ["small", "needs", "too", "but", "however", "issue", "problem"]
        
        sentiment = "neutral"
        for word in positive_words:
            if word in sentence.lower():
                sentiment = "positive"
                break
        
        for word in negative_words:
            if word in sentence.lower():
                sentiment = "negative"
                break
        
        key_points.append(f"{sentiment.capitalize()}: {sentence}")
    
    # Format the summary
    summary = "Buyer Feedback Summary:\n\n"
    summary += "\n".join(key_points)
    
    return summary

async def notify_listing_agent(feedback_id: str) -> Dict[str, Any]:
    """
    Notify the listing agent about the feedback.
    In a real implementation, this would send an email, SMS, or notification.
    For now, we'll simulate the process.
    """
    feedback = get_feedback(feedback_id)
    if not feedback:
        logging.error(f"Feedback not found: {feedback_id}")
        return {"error": "Feedback not found"}
    
    # Get the task and property visit
    task = get_task(feedback.task_id)
    if not task:
        logging.error(f"Task not found: {feedback.task_id}")
        return {"error": "Task not found"}
    
    property_visit = get_property_visit(task.visit_id)
    if not property_visit:
        logging.error(f"Property visit not found: {task.visit_id}")
        return {"error": "Property visit not found"}
    
    # In a real implementation, this would send a notification to the listing agent
    # For now, we'll log the notification
    logging.info(f"Notifying listing agent {property_visit.sellside_agent_name} about feedback for {property_visit.address}")
    logging.info(f"Feedback: {feedback.processed_feedback}")
    
    # Mark the feedback as sent
    mark_feedback_as_sent(feedback_id)
    
    # Update the task status to completed
    update_task_status(feedback.task_id, TaskStatus.COMPLETED)
    
    return {"status": "listing_agent_notified", "feedback_id": feedback_id}

async def get_tour_journal(tour_id: str) -> List[Dict[str, Any]]:
    """
    Get a chronological journal of all property visits and feedback for a tour.
    """
    from app.models import get_property_visits_by_tour
    
    # Get all property visits for the tour
    property_visits = get_property_visits_by_tour(tour_id)
    
    journal_entries = []
    
    for visit in property_visits:
        # Get all tasks for this visit
        tasks = get_tasks_by_visit(visit.id)
        
        # Create a journal entry for the property visit
        visit_entry = {
            "type": "property_visit",
            "timestamp": visit.scheduled_arrival,
            "address": visit.address,
            "status": visit.status,
            "scheduled_arrival": visit.scheduled_arrival,
            "scheduled_departure": visit.scheduled_departure,
            "actual_arrival": visit.actual_arrival,
            "actual_departure": visit.actual_departure,
            "sellside_agent_name": visit.sellside_agent_name,
            "feedback": []
        }
        
        # Add feedback for each task
        for task in tasks:
            if task.task_type == "feedback_collection":
                # Get feedback for this task
                from app.models import get_feedback_by_task
                feedback_entries = get_feedback_by_task(task.id)
                
                for feedback in feedback_entries:
                    feedback_entry = {
                        "type": "feedback",
                        "timestamp": feedback.timestamp,
                        "source": feedback.feedback_source,
                        "raw_feedback": feedback.raw_feedback,
                        "processed_feedback": feedback.processed_feedback,
                        "sent_to_agent": feedback.sent_to_agent
                    }
                    visit_entry["feedback"].append(feedback_entry)
        
        journal_entries.append(visit_entry)
    
    # Sort journal entries by timestamp
    journal_entries.sort(key=lambda x: x["timestamp"])
    
    return journal_entries

async def process_unsent_feedback() -> Dict[str, Any]:
    """
    Process all unsent feedback and send notifications.
    This is a wrapper around the NotificationService method.
    
    Returns:
        Dict: Processing result with status and counts
    """
    from app.models.database import get_db_connection
    from app.services.notification_service import NotificationService
    
    # Create notification service
    db = get_db_connection()
    notification_service = NotificationService(db)
    
    # Process unsent feedback
    result = await notification_service.process_unsent_feedback()
    return result
