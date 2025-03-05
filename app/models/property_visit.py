from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import datetime

from app.models.database import get_db_connection, generate_id, current_timestamp

class PropertyVisitBase(BaseModel):
    tour_id: str
    address: str
    property_id: Optional[str] = None
    scheduled_arrival: str
    scheduled_departure: str
    status: str = "scheduled"  # scheduled, arrived, completed, cancelled, skipped
    sellside_agent_id: Optional[str] = None
    sellside_agent_name: Optional[str] = None
    contact_method: Optional[str] = None
    confirmation_status: Optional[str] = None
    constraint_indicator: Optional[str] = None
    square_footage: Optional[int] = None
    video_url: Optional[str] = None

class PropertyVisitCreate(PropertyVisitBase):
    pass

class PropertyVisit(PropertyVisitBase):
    id: str
    actual_arrival: Optional[str] = None
    actual_departure: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

def create_property_visit(visit: PropertyVisitCreate) -> PropertyVisit:
    """Create a new property visit in the database."""
    visit_id = generate_id()
    now = current_timestamp()
    
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO property_visits (
                id, tour_id, address, property_id, scheduled_arrival, scheduled_departure,
                status, sellside_agent_id, sellside_agent_name, contact_method,
                confirmation_status, constraint_indicator, square_footage, video_url,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                visit_id, visit.tour_id, visit.address, visit.property_id,
                visit.scheduled_arrival, visit.scheduled_departure, visit.status,
                visit.sellside_agent_id, visit.sellside_agent_name, visit.contact_method,
                visit.confirmation_status, visit.constraint_indicator, visit.square_footage,
                visit.video_url, now, now
            )
        )
        conn.commit()
    
    return PropertyVisit(
        id=visit_id,
        tour_id=visit.tour_id,
        address=visit.address,
        property_id=visit.property_id,
        scheduled_arrival=visit.scheduled_arrival,
        scheduled_departure=visit.scheduled_departure,
        status=visit.status,
        sellside_agent_id=visit.sellside_agent_id,
        sellside_agent_name=visit.sellside_agent_name,
        contact_method=visit.contact_method,
        confirmation_status=visit.confirmation_status,
        constraint_indicator=visit.constraint_indicator,
        square_footage=visit.square_footage,
        video_url=visit.video_url,
        created_at=now,
        updated_at=now
    )

def get_property_visit(visit_id: str) -> Optional[PropertyVisit]:
    """Get a property visit by ID."""
    with get_db_connection() as conn:
        result = conn.execute("SELECT * FROM property_visits WHERE id = ?", (visit_id,)).fetchone()
    
    if result:
        return PropertyVisit(**result)
    return None

def update_property_visit(visit_id: str, data: Dict[str, Any]) -> Optional[PropertyVisit]:
    """Update a property visit with the provided data."""
    if not data:
        return get_property_visit(visit_id)
    
    data["updated_at"] = current_timestamp()
    
    set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
    values = list(data.values()) + [visit_id]
    
    with get_db_connection() as conn:
        conn.execute(
            f"UPDATE property_visits SET {set_clause} WHERE id = ?",
            values
        )
        conn.commit()
    
    return get_property_visit(visit_id)

def get_property_visits_by_tour(tour_id: str) -> List[PropertyVisit]:
    """Get all property visits for a specific tour."""
    with get_db_connection() as conn:
        results = conn.execute(
            "SELECT * FROM property_visits WHERE tour_id = ? ORDER BY scheduled_arrival",
            (tour_id,)
        ).fetchall()
    
    return [PropertyVisit(**result) for result in results]

def record_arrival(visit_id: str, arrival_time: str) -> Optional[PropertyVisit]:
    """Record the actual arrival time at a property."""
    return update_property_visit(
        visit_id,
        {
            "actual_arrival": arrival_time,
            "status": "arrived"
        }
    )

def record_departure(visit_id: str, departure_time: str) -> Optional[PropertyVisit]:
    """Record the actual departure time from a property."""
    return update_property_visit(
        visit_id,
        {
            "actual_departure": departure_time,
            "status": "completed"
        }
    )

def get_next_property_visit(tour_id: str) -> Optional[PropertyVisit]:
    """Get the next scheduled property visit for a tour."""
    with get_db_connection() as conn:
        result = conn.execute(
            """
            SELECT * FROM property_visits
            WHERE tour_id = ? AND status = 'scheduled'
            ORDER BY scheduled_arrival
            LIMIT 1
            """,
            (tour_id,)
        ).fetchone()
    
    if result:
        return PropertyVisit(**result)
    return None

def get_current_property_visit(tour_id: str) -> Optional[PropertyVisit]:
    """Get the current property visit (status = 'arrived') for a tour."""
    with get_db_connection() as conn:
        result = conn.execute(
            """
            SELECT * FROM property_visits
            WHERE tour_id = ? AND status = 'arrived'
            LIMIT 1
            """,
            (tour_id,)
        ).fetchone()
    
    if result:
        return PropertyVisit(**result)
    return None
