from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import datetime
import enum

from app.models.database import get_db_connection, generate_id, current_timestamp

class TaskType(str, enum.Enum):
    PROPERTY_TOUR = "property_tour"
    FEEDBACK_COLLECTION = "feedback_collection"
    LISTING_AGENT_NOTIFICATION = "listing_agent_notification"
    BUYER_FOLLOWUP = "buyer_followup"

class TaskStatus(str, enum.Enum):
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"

class TaskBase(BaseModel):
    visit_id: str
    task_type: str
    status: str = TaskStatus.SCHEDULED
    scheduled_time: str
    shipment_id: Optional[str] = None

class TaskCreate(TaskBase):
    pass

class Task(TaskBase):
    id: str
    completed_time: Optional[str] = None
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class TaskUpdate(BaseModel):
    status: Optional[str] = None
    completed_time: Optional[str] = None
    shipment_id: Optional[str] = None

def create_task(task: TaskCreate) -> Task:
    """Create a new task in the database."""
    task_id = generate_id()
    now = current_timestamp()
    
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO tasks (
                id, visit_id, task_type, status, scheduled_time,
                shipment_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                task_id, task.visit_id, task.task_type, task.status,
                task.scheduled_time, task.shipment_id, now, now
            )
        )
        conn.commit()
    
    return Task(
        id=task_id,
        visit_id=task.visit_id,
        task_type=task.task_type,
        status=task.status,
        scheduled_time=task.scheduled_time,
        shipment_id=task.shipment_id,
        created_at=now,
        updated_at=now
    )

def get_task(task_id: str) -> Optional[Task]:
    """Get a task by ID."""
    with get_db_connection() as conn:
        result = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    
    if result:
        return Task(**result)
    return None

def update_task(task_id: str, data: Dict[str, Any]) -> Optional[Task]:
    """Update a task with the provided data."""
    if not data:
        return get_task(task_id)
    
    data["updated_at"] = current_timestamp()
    
    set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
    values = list(data.values()) + [task_id]
    
    with get_db_connection() as conn:
        conn.execute(
            f"UPDATE tasks SET {set_clause} WHERE id = ?",
            values
        )
        conn.commit()
    
    return get_task(task_id)

def update_task_status(task_id: str, status: str, completed_time: Optional[str] = None) -> Optional[Task]:
    """Update the status of a task."""
    data = {"status": status}
    
    if status == TaskStatus.COMPLETED and completed_time:
        data["completed_time"] = completed_time
    elif status == TaskStatus.COMPLETED and not completed_time:
        data["completed_time"] = current_timestamp()
    
    return update_task(task_id, data)

def get_tasks_by_visit(visit_id: str) -> List[Task]:
    """Get all tasks for a specific property visit."""
    with get_db_connection() as conn:
        results = conn.execute(
            "SELECT * FROM tasks WHERE visit_id = ? ORDER BY scheduled_time",
            (visit_id,)
        ).fetchall()
    
    return [Task(**result) for result in results]

def get_tasks_by_type(task_type: str) -> List[Task]:
    """Get all tasks of a specific type."""
    with get_db_connection() as conn:
        results = conn.execute(
            "SELECT * FROM tasks WHERE task_type = ? ORDER BY scheduled_time",
            (task_type,)
        ).fetchall()
    
    return [Task(**result) for result in results]

def get_pending_tasks() -> List[Task]:
    """Get all tasks that are scheduled or in progress."""
    with get_db_connection() as conn:
        results = conn.execute(
            """
            SELECT * FROM tasks
            WHERE status IN (?, ?)
            ORDER BY scheduled_time
            """,
            (TaskStatus.SCHEDULED, TaskStatus.IN_PROGRESS)
        ).fetchall()
    
    return [Task(**result) for result in results]

def get_tasks_by_shipment(shipment_id: str) -> List[Task]:
    """Get all tasks associated with a specific shipment."""
    with get_db_connection() as conn:
        results = conn.execute(
            "SELECT * FROM tasks WHERE shipment_id = ?",
            (shipment_id,)
        ).fetchall()
    
    return [Task(**result) for result in results]

def create_property_tour_task(visit_id: str, scheduled_time: str) -> Task:
    """Create a property tour task for a visit."""
    task = TaskCreate(
        visit_id=visit_id,
        task_type=TaskType.PROPERTY_TOUR,
        status=TaskStatus.SCHEDULED,
        scheduled_time=scheduled_time
    )
    return create_task(task)

def create_feedback_task(visit_id: str, scheduled_time: str) -> Task:
    """Create a feedback collection task for a visit."""
    task = TaskCreate(
        visit_id=visit_id,
        task_type=TaskType.FEEDBACK_COLLECTION,
        status=TaskStatus.SCHEDULED,
        scheduled_time=scheduled_time
    )
    return create_task(task)
