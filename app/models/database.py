import os
import sqlite3
from contextlib import contextmanager
import json
import uuid

from app.utils.time_utils import current_timestamp

# Database setup
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "reanna_router.db")

def dict_factory(cursor, row):
    """Convert database row objects to a dictionary."""
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = dict_factory
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Initialize the database with required tables."""
    with get_db_connection() as conn:
        # Create tours table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS tours (
            id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL,
            status TEXT NOT NULL,
            route_data TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        # Create property_visits table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS property_visits (
            id TEXT PRIMARY KEY,
            tour_id TEXT NOT NULL,
            address TEXT NOT NULL,
            property_id TEXT,
            scheduled_arrival TEXT NOT NULL,
            scheduled_departure TEXT NOT NULL,
            actual_arrival TEXT,
            actual_departure TEXT,
            status TEXT NOT NULL,
            sellside_agent_id TEXT,
            sellside_agent_name TEXT,
            contact_method TEXT,
            confirmation_status TEXT,
            constraint_indicator TEXT,
            square_footage INTEGER,
            video_url TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (tour_id) REFERENCES tours (id)
        )
        ''')
        
        # Create tasks table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id TEXT PRIMARY KEY,
            visit_id TEXT NOT NULL,
            task_type TEXT NOT NULL,
            status TEXT NOT NULL,
            scheduled_time TEXT NOT NULL,
            completed_time TEXT,
            shipment_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (visit_id) REFERENCES property_visits (id)
        )
        ''')
        
        # Create feedback table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS feedback (
            id TEXT PRIMARY KEY,
            task_id TEXT NOT NULL,
            raw_feedback TEXT,
            processed_feedback TEXT,
            feedback_source TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            sent_to_agent BOOLEAN DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY (task_id) REFERENCES tasks (id)
        )
        ''')
        
        conn.commit()

def generate_id():
    """Generate a unique ID for database records."""
    return uuid.uuid4().hex

# Initialize the database if it doesn't exist
if not os.path.exists(DB_PATH):
    init_db()
