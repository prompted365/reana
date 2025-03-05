from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
import datetime
import logging

from app.models import (
    Tour, TourCreate, create_tour, get_tour, update_tour,
    get_tours_by_agent, get_active_tours
)
from app.services import optimize_tour

router = APIRouter(prefix="/tours", tags=["tours"])

@router.post("/", response_model=Dict[str, Any])
async def create_new_tour(
    agent_id: str,
    start_time: str,
    end_time: str,
    agent_home: str,
    properties: List[Dict[str, Any]]
):
    """
    Create a new tour and optimize the schedule.
    """
    # Validate the number of properties
    if len(properties) > 7:
        raise HTTPException(status_code=400, detail="Maximum of 7 properties allowed")
    
    try:
        # Parse and validate times
        start_dt = datetime.datetime.fromisoformat(start_time)
        end_dt = datetime.datetime.fromisoformat(end_time)
        if start_dt >= end_dt:
            raise HTTPException(status_code=400, detail="End time must be after start time")
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format. Expected ISO 8601 format.")
    
    # Create the tour
    tour = TourCreate(
        agent_id=agent_id,
        start_time=start_time,
        end_time=end_time,
        status="scheduled"
    )
    
    created_tour = create_tour(tour)
    
    # Optimize the tour
    try:
        optimization_result = optimize_tour(created_tour, properties, agent_home)
        
        # Update the tour with the route data
        update_tour(created_tour.id, {"route_data": str(optimization_result)})
        
        # Return the optimization result
        return {
            "tour_id": created_tour.id,
            "optimization_result": optimization_result
        }
    except Exception as e:
        logging.error(f"Error optimizing tour: {e}")
        # If optimization fails, still return the tour ID
        return {
            "tour_id": created_tour.id,
            "error": str(e)
        }

@router.get("/{tour_id}", response_model=Dict[str, Any])
async def get_tour_details(tour_id: str):
    """
    Get details of a specific tour.
    """
    tour = get_tour(tour_id)
    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")
    
    # Get property visits for this tour
    from app.models import get_property_visits_by_tour
    property_visits = get_property_visits_by_tour(tour_id)
    
    # Format the response
    result = {
        "tour_id": tour.id,
        "agent_id": tour.agent_id,
        "start_time": tour.start_time,
        "end_time": tour.end_time,
        "status": tour.status,
        "property_visits": []
    }
    
    for visit in property_visits:
        # Get tasks for this visit
        from app.models import get_tasks_by_visit
        tasks = get_tasks_by_visit(visit.id)
        
        # Format the visit
        visit_data = {
            "visit_id": visit.id,
            "address": visit.address,
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
            
            visit_data["tasks"].append(task_data)
        
        result["property_visits"].append(visit_data)
    
    return result

@router.get("/", response_model=List[Dict[str, Any]])
async def get_tours(agent_id: Optional[str] = None, active_only: bool = False):
    """
    Get all tours, optionally filtered by agent ID or active status.
    """
    if agent_id:
        tours = get_tours_by_agent(agent_id)
    elif active_only:
        tours = get_active_tours()
    else:
        # Get all tours (not implemented yet)
        tours = []
    
    # Format the response
    result = []
    for tour in tours:
        tour_data = {
            "tour_id": tour.id,
            "agent_id": tour.agent_id,
            "start_time": tour.start_time,
            "end_time": tour.end_time,
            "status": tour.status
        }
        result.append(tour_data)
    
    return result

@router.put("/{tour_id}/status", response_model=Dict[str, Any])
async def update_tour_status(tour_id: str, status: str):
    """
    Update the status of a tour.
    """
    valid_statuses = ["scheduled", "in_progress", "completed", "cancelled"]
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}")
    
    tour = get_tour(tour_id)
    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")
    
    updated_tour = update_tour(tour_id, {"status": status})
    
    return {
        "tour_id": updated_tour.id,
        "status": updated_tour.status
    }

@router.get("/{tour_id}/journal", response_model=Dict[str, Any])
async def get_tour_journal_entries(tour_id: str):
    """
    Get the journal entries for a tour.
    """
    tour = get_tour(tour_id)
    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")
    
    # Get the tour journal
    from app.services import get_tour_journal
    journal = await get_tour_journal(tour_id)
    
    return {
        "tour_id": tour_id,
        "journal_entries": journal
    }
