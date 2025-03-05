from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import datetime
import json

from app.models.database import get_db_connection, generate_id, current_timestamp

class TourBase(BaseModel):
    agent_id: str
    start_time: str
    end_time: str
    status: str = "scheduled"  # scheduled, in_progress, completed, cancelled

class TourCreate(TourBase):
    pass

class Tour(TourBase):
    id: str
    route_data: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

def create_tour(tour: TourCreate) -> Tour:
    """Create a new tour in the database."""
    tour_id = generate_id()
    now = current_timestamp()
    
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO tours (id, agent_id, start_time, end_time, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (tour_id, tour.agent_id, tour.start_time, tour.end_time, tour.status, now, now)
        )
        conn.commit()
    
    return Tour(
        id=tour_id,
        agent_id=tour.agent_id,
        start_time=tour.start_time,
        end_time=tour.end_time,
        status=tour.status,
        created_at=now,
        updated_at=now
    )

def get_tour(tour_id: str) -> Optional[Tour]:
    """Get a tour by ID."""
    with get_db_connection() as conn:
        result = conn.execute("SELECT * FROM tours WHERE id = ?", (tour_id,)).fetchone()
    
    if result:
        return Tour(**result)
    return None

def update_tour(tour_id: str, data: Dict[str, Any]) -> Optional[Tour]:
    """Update a tour with the provided data."""
    if not data:
        return get_tour(tour_id)
    
    data["updated_at"] = current_timestamp()
    
    set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
    values = list(data.values()) + [tour_id]
    
    with get_db_connection() as conn:
        conn.execute(
            f"UPDATE tours SET {set_clause} WHERE id = ?",
            values
        )
        conn.commit()
    
    return get_tour(tour_id)

def update_tour_route_data(tour_id: str, route_data: Dict[str, Any]) -> Optional[Tour]:
    """Update the route_data field of a tour."""
    route_data_json = json.dumps(route_data)
    return update_tour(tour_id, {"route_data": route_data_json})

def get_tours_by_agent(agent_id: str) -> List[Tour]:
    """Get all tours for a specific agent."""
    with get_db_connection() as conn:
        results = conn.execute("SELECT * FROM tours WHERE agent_id = ? ORDER BY start_time DESC", (agent_id,)).fetchall()
    
    return [Tour(**result) for result in results]

def get_active_tours() -> List[Tour]:
    """Get all active tours (scheduled or in_progress)."""
    with get_db_connection() as conn:
        results = conn.execute(
            "SELECT * FROM tours WHERE status IN ('scheduled', 'in_progress') ORDER BY start_time"
        ).fetchall()
    
    return [Tour(**result) for result in results]
