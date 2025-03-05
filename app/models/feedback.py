from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import datetime
import enum

from app.models.database import get_db_connection, generate_id, current_timestamp

class FeedbackSource(str, enum.Enum):
    SMS = "sms"
    VOICE = "voice"
    APP = "app"
    EMAIL = "email"
    MANUAL = "manual"

class FeedbackBase(BaseModel):
    task_id: str
    raw_feedback: Optional[str] = None
    processed_feedback: Optional[str] = None
    feedback_source: str
    timestamp: str
    sent_to_agent: bool = False

class FeedbackCreate(FeedbackBase):
    pass

class Feedback(FeedbackBase):
    id: str
    created_at: str
    updated_at: str

    class Config:
        orm_mode = True

class FeedbackUpdate(BaseModel):
    raw_feedback: Optional[str] = None
    processed_feedback: Optional[str] = None
    sent_to_agent: Optional[bool] = None

def create_feedback(feedback: FeedbackCreate) -> Feedback:
    """Create a new feedback entry in the database."""
    feedback_id = generate_id()
    now = current_timestamp()
    
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO feedback (
                id, task_id, raw_feedback, processed_feedback,
                feedback_source, timestamp, sent_to_agent,
                created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                feedback_id, feedback.task_id, feedback.raw_feedback,
                feedback.processed_feedback, feedback.feedback_source,
                feedback.timestamp, feedback.sent_to_agent, now, now
            )
        )
        conn.commit()
    
    return Feedback(
        id=feedback_id,
        task_id=feedback.task_id,
        raw_feedback=feedback.raw_feedback,
        processed_feedback=feedback.processed_feedback,
        feedback_source=feedback.feedback_source,
        timestamp=feedback.timestamp,
        sent_to_agent=feedback.sent_to_agent,
        created_at=now,
        updated_at=now
    )

def get_feedback(feedback_id: str) -> Optional[Feedback]:
    """Get a feedback entry by ID."""
    with get_db_connection() as conn:
        result = conn.execute("SELECT * FROM feedback WHERE id = ?", (feedback_id,)).fetchone()
    
    if result:
        return Feedback(**result)
    return None

def update_feedback(feedback_id: str, data: Dict[str, Any]) -> Optional[Feedback]:
    """Update a feedback entry with the provided data."""
    if not data:
        return get_feedback(feedback_id)
    
    data["updated_at"] = current_timestamp()
    
    set_clause = ", ".join([f"{key} = ?" for key in data.keys()])
    values = list(data.values()) + [feedback_id]
    
    with get_db_connection() as conn:
        conn.execute(
            f"UPDATE feedback SET {set_clause} WHERE id = ?",
            values
        )
        conn.commit()
    
    return get_feedback(feedback_id)

def get_feedback_by_task(task_id: str) -> List[Feedback]:
    """Get all feedback entries for a specific task."""
    with get_db_connection() as conn:
        results = conn.execute(
            "SELECT * FROM feedback WHERE task_id = ? ORDER BY timestamp DESC",
            (task_id,)
        ).fetchall()
    
    return [Feedback(**result) for result in results]

def get_unsent_feedback() -> List[Feedback]:
    """Get all feedback entries that haven't been sent to agents."""
    with get_db_connection() as conn:
        results = conn.execute(
            """
            SELECT * FROM feedback
            WHERE sent_to_agent = 0 AND processed_feedback IS NOT NULL
            ORDER BY timestamp
            """
        ).fetchall()
    
    return [Feedback(**result) for result in results]

def mark_feedback_as_sent(feedback_id: str) -> Optional[Feedback]:
    """Mark a feedback entry as sent to the agent."""
    return update_feedback(feedback_id, {"sent_to_agent": True})

def add_processed_feedback(feedback_id: str, processed_feedback: str) -> Optional[Feedback]:
    """Add processed (AI-summarized) feedback to an entry."""
    return update_feedback(feedback_id, {"processed_feedback": processed_feedback})

def create_sms_feedback(task_id: str, raw_feedback: str) -> Feedback:
    """Create a feedback entry from SMS."""
    feedback = FeedbackCreate(
        task_id=task_id,
        raw_feedback=raw_feedback,
        feedback_source=FeedbackSource.SMS,
        timestamp=current_timestamp()
    )
    return create_feedback(feedback)

def create_voice_feedback(task_id: str, raw_feedback: str) -> Feedback:
    """Create a feedback entry from voice transcription."""
    feedback = FeedbackCreate(
        task_id=task_id,
        raw_feedback=raw_feedback,
        feedback_source=FeedbackSource.VOICE,
        timestamp=current_timestamp()
    )
    return create_feedback(feedback)
