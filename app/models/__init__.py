from app.models.database import init_db, get_db_connection, generate_id, current_timestamp
from app.models.tour import Tour, TourCreate, create_tour, get_tour, update_tour, get_tours_by_agent, get_active_tours
from app.models.property_visit import (
    PropertyVisit, PropertyVisitCreate, create_property_visit, get_property_visit,
    update_property_visit, get_property_visits_by_tour, record_arrival, record_departure,
    get_next_property_visit, get_current_property_visit
)
from app.models.task import (
    Task, TaskCreate, TaskUpdate, TaskType, TaskStatus, create_task, get_task,
    update_task, update_task_status, get_tasks_by_visit, get_tasks_by_type,
    get_pending_tasks, get_tasks_by_shipment, create_property_tour_task, create_feedback_task
)
from app.models.feedback import (
    Feedback, FeedbackCreate, FeedbackUpdate, FeedbackSource, create_feedback, get_feedback,
    update_feedback, get_feedback_by_task, get_unsent_feedback, mark_feedback_as_sent,
    add_processed_feedback, create_sms_feedback, create_voice_feedback
)

# Initialize the database
init_db()
