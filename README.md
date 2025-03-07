# REanna Router

A FastAPI application that optimizes real estate tour schedules using Google's Route Optimization API, with enhanced task management and feedback collection capabilities.

## Features

- Optimizes property viewing schedules for real estate agents
- Uses Google Maps APIs for geocoding and route optimization
- Maps shipments to discrete tasks for flexible tour management
- Collects and processes buyer feedback in real-time
- Notifies listing agents about property feedback
- Maintains a tour journal with chronological visit and feedback data
- Supports different agent preferences (optimize, furthest, closest)

## Architecture

REanna Router uses a task-based architecture that maps Google Cloud Fleet Routing "shipments" to discrete tasks in a property tour workflow:

- **Tours**: Represent a complete property viewing schedule for an agent
- **Property Visits**: Individual stops at properties within a tour
- **Tasks**: Discrete activities associated with property visits (touring, feedback collection, etc.)
- **Feedback**: Buyer feedback collected via SMS, voice, or other methods

This architecture allows for flexible scheduling, real-time updates, and parallel AI-driven feedback processing.

## Core Components

### Models

#### Tour Model

- **Classes**: `TourBase`, `TourCreate`, `Tour`
- **Functions**:
  - `create_tour`: Creates a new tour in the database
  - `get_tour`: Retrieves a tour by ID
  - `update_tour`: Updates a tour with provided data
  - `update_tour_route_data`: Updates the route data field of a tour
  - `get_tours_by_agent`: Gets all tours for a specific agent
  - `get_active_tours`: Gets all active tours (scheduled or in progress)

#### Property Visit Model

- **Classes**: `PropertyVisitBase`, `PropertyVisitCreate`, `PropertyVisit`
- **Functions**:
  - `create_property_visit`: Creates a new property visit in the database
  - `get_property_visit`: Retrieves a property visit by ID
  - `update_property_visit`: Updates a property visit with provided data
  - `get_property_visits_by_tour`: Gets all property visits for a specific tour
  - `record_arrival`: Records the actual arrival time at a property
  - `record_departure`: Records the actual departure time from a property
  - `get_next_property_visit`: Gets the next scheduled property visit for a tour
  - `get_current_property_visit`: Gets the current property visit for a tour

#### Task Model

- **Classes**: `TaskBase`, `TaskCreate`, `Task`, `TaskUpdate`, `TaskType`, `TaskStatus`
- **Functions**:
  - `create_task`: Creates a new task in the database
  - `get_task`: Retrieves a task by ID
  - `update_task`: Updates a task with provided data
  - `update_task_status`: Updates the status of a task
  - `get_tasks_by_visit`: Gets all tasks for a specific property visit
  - `get_tasks_by_type`: Gets all tasks of a specific type
  - `get_pending_tasks`: Gets all tasks that are scheduled or in progress
  - `get_tasks_by_shipment`: Gets all tasks associated with a specific shipment
  - `create_property_tour_task`: Creates a property tour task for a visit
  - `create_feedback_task`: Creates a feedback collection task for a visit

#### Feedback Model

- **Classes**: `FeedbackBase`, `FeedbackCreate`, `Feedback`, `FeedbackUpdate`, `FeedbackSource`
- **Functions**:
  - `create_feedback`: Creates a new feedback entry in the database
  - `get_feedback`: Retrieves a feedback entry by ID
  - `update_feedback`: Updates a feedback entry with provided data
  - `get_feedback_by_task`: Gets all feedback entries for a specific task
  - `get_unsent_feedback`: Gets all feedback entries that haven't been sent to agents
  - `mark_feedback_as_sent`: Marks a feedback entry as sent to the agent
  - `add_processed_feedback`: Adds processed (AI-summarized) feedback to an entry
  - `create_sms_feedback`: Creates a feedback entry from SMS
  - `create_voice_feedback`: Creates a feedback entry from voice transcription

#### Database Model

- **Functions**:
  - `dict_factory`: Converts database row objects to a dictionary
  - `get_db_connection`: Context manager for database connections
  - `init_db`: Initializes the database with required tables
  - `generate_id`: Generates a unique ID for database records

### Services

#### Optimization Service

- **Functions**:
  - `geocode_address`: Converts address to lat/lng using the Geocoding API
  - `compute_visit_duration_seconds`: Computes visit duration based on property square footage (in seconds)
  - `compute_visit_duration_minutes`: Computes visit duration based on property square footage (in minutes)
  - `map_properties_to_shipments`: Maps property visits to shipments for the Route Optimization API
  - `call_route_optimization_api`: Calls the Google Maps Route Optimization API
  - `parse_optimization_response`: Parses the Route Optimization API response and updates the database
  - `optimize_tour`: Optimizes a tour schedule using the Google Route Optimization API

#### Feedback Service

- **Functions**:
  - `trigger_feedback_collection`: Triggers feedback collection for a completed property tour task
  - `collect_sms_feedback`: Collects feedback via SMS
  - `collect_voice_feedback`: Collects feedback via voice call
  - `process_feedback`: Processes raw feedback using AI
  - `summarize_feedback_with_ai`: Summarizes raw feedback using AI
  - `notify_listing_agent`: Notifies the listing agent about feedback
  - `get_tour_journal`: Gets a chronological journal of all property visits and feedback for a tour

#### Notification Service

- **Classes**: `NotificationType`, `NotificationMethod`
- **Functions**:
  - `notify_listing_agent`: Sends a notification to a listing agent
  - `notify_buyer`: Sends a notification to a buyer
  - `send_email_notification`: Sends an email notification
  - `send_sms_notification`: Sends an SMS notification
  - `send_push_notification`: Sends a push notification
  - `send_feedback_notification`: Sends a notification about feedback to the listing agent
  - `send_tour_summary`: Sends a summary of the tour to the buyer and listing agents
  - `process_unsent_feedback`: Processes all unsent feedback and sends notifications

### Utilities

#### Time Utilities

- **Functions**:
  - `current_timestamp`: Gets current timestamp in ISO format
  - `to_utc_z`: Converts a datetime object or ISO 8601 string to UTC ISO 8601 format with a trailing "Z"
  - `from_utc_z`: Converts a UTC ISO 8601 string with a trailing "Z" to a datetime object
  - `seconds_to_minutes`: Converts seconds to minutes, rounding up to the nearest minute
  - `minutes_to_seconds`: Converts minutes to seconds
  - `meters_to_kilometers`: Converts meters to kilometers, rounding to 1 decimal place
  - `kilometers_to_meters`: Converts kilometers to meters
  - `format_duration`: Formats a duration in seconds to a human-readable string
  - `format_time`: Formats a datetime object or ISO 8601 string to a human-readable time string
  - `format_date`: Formats a datetime object or ISO 8601 string to a human-readable date string
  - `parse_time`: Parses a time string in HH:MM format to a time object
  - `combine_date_time`: Combines a date object with a time string in HH:MM format

## API Endpoints

REanna Router provides a comprehensive set of API endpoints for managing tours, property visits, tasks, and feedback:

### Tours

- `POST /tours/`: Create a new tour and optimize the schedule
- `GET /tours/{tour_id}`: Get details of a specific tour
- `GET /tours/`: Get all tours, optionally filtered by agent ID or active status
- `PUT /tours/{tour_id}/status`: Update the status of a tour
- `GET /tours/{tour_id}/journal`: Get the journal entries for a tour

### Property Visits

- `GET /property-visits/`: Get all property visits for a tour
- `GET /property-visits/{visit_id}`: Get details of a specific property visit
- `POST /property-visits/`: Create a new property visit
- `PUT /property-visits/{visit_id}/arrival`: Record the actual arrival time at a property
- `PUT /property-visits/{visit_id}/departure`: Record the actual departure time from a property
- `PUT /property-visits/{visit_id}/status`: Update the status of a property visit
- `GET /property-visits/tour/{tour_id}/next`: Get the next scheduled property visit for a tour
- `GET /property-visits/tour/{tour_id}/current`: Get the current property visit for a tour

### Tasks

- `GET /tasks/`: Get tasks, optionally filtered by visit ID, task type, or pending status
- `GET /tasks/{task_id}`: Get details of a specific task
- `PUT /tasks/{task_id}/status`: Update the status of a task
- `PUT /tasks/{task_id}`: Update details of a task
- `POST /tasks/property-tour`: Create a property tour task
- `POST /tasks/feedback`: Create a feedback collection task

### Feedback

- `GET /feedback/`: Get feedback entries, optionally filtered by task ID or unsent status
- `GET /feedback/{feedback_id}`: Get details of a specific feedback entry
- `POST /feedback/sms`: Submit feedback via SMS
- `POST /feedback/voice`: Submit feedback via voice transcription
- `PUT /feedback/{feedback_id}/process`: Process a feedback entry using AI
- `PUT /feedback/{feedback_id}/notify`: Send a notification about feedback to the listing agent
- `PUT /feedback/{feedback_id}`: Update a feedback entry
- `POST /feedback/process-unsent`: Process all unsent feedback and send notifications

### Legacy Endpoint

For backward compatibility with the original API:

- `POST /optimize`: Legacy endpoint that accepts the original request format

## Prerequisites

- Docker and Docker Compose
- Google Cloud Platform account with the following APIs enabled:
  - Geocoding API
  - Routes API
  - Route Optimization API
- Google Cloud credentials
- SQLite (for development) or another database (for production)

## Environment Variables

Create a `.env` file with the following variables:

```bash
GOOGLE_API_KEY=your_google_api_key
GCP_PROJECT_ID=your_gcp_project_id
GHL_LOCATION_ID=your_ghl_location_id
GHL_TOKEN=your_ghl_token
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google-credentials.json
```

## Google Cloud Authentication

The easiest way to set up Google Cloud authentication is to use the included setup script:

```bash
# Make the script executable if needed
chmod +x setup_gcp_credentials.sh

# Run the setup script
./setup_gcp_credentials.sh
```

This script will:

1. Check if you're logged in to Google Cloud
2. Verify the required APIs are enabled
3. Help you create a service account with the necessary permissions
4. Generate and download credentials
5. Update your `.env` file automatically

### Manual Setup Options

If you prefer to set up authentication manually, there are two approaches:

#### Option 1: Service Account Key File (Recommended for Production)

1. Create a service account with appropriate permissions in Google Cloud Console
   - Required roles: `roles/maps.routeOptimizer`, `roles/maps.routesUser`, `roles/maps.viewer`
2. Download the service account key as `google-credentials.json` and place it in the project root
3. Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable in your `.env` file to point to this file

The Docker setup will automatically mount this file into the container.

#### Option 2: Application Default Credentials (For Development)

For local development, you can authenticate with Google Cloud using the gcloud CLI:

```bash
gcloud auth application-default login
```

Then set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to the default credentials file:

```txt
GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/application_default_credentials.json
```

## Running with Docker

Build and start the application:

```bash
docker-compose up -d
```

The API will be available at <http://localhost:8000>

## Testing

You can test the API using the included `test.py` script:

```bash
python test.py
```

This will send a sample request to the API and generate an HTML schedule in the `tours/` directory.

## Development

For local development without Docker:

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python main.py
```

## Database Schema

REanna Router uses SQLite for development, but can be configured to use other databases for production. The database schema includes the following tables:

### Tours Table

- `id`: Primary key
- `agent_id`: ID of the agent conducting the tour
- `start_time`: Start time of the tour
- `end_time`: End time of the tour
- `status`: Status of the tour (scheduled, in_progress, completed, cancelled)
- `route_data`: JSON data containing the optimized route
- `created_at`: Timestamp when the record was created
- `updated_at`: Timestamp when the record was last updated

### Property Visits Table

- `id`: Primary key
- `tour_id`: Foreign key referencing the tour
- `address`: Address of the property
- `property_id`: ID of the property (optional)
- `scheduled_arrival`: Scheduled arrival time at the property
- `scheduled_departure`: Scheduled departure time from the property
- `actual_arrival`: Actual arrival time at the property (optional)
- `actual_departure`: Actual departure time from the property (optional)
- `status`: Status of the visit (scheduled, arrived, completed, cancelled, skipped)
- `sellside_agent_id`: ID of the listing agent (optional)
- `sellside_agent_name`: Name of the listing agent (optional)
- `contact_method`: Preferred contact method for the listing agent (optional)
- `confirmation_status`: Status of the showing confirmation (optional)
- `constraint_indicator`: Any constraints on the showing (optional)
- `square_footage`: Square footage of the property (optional)
- `video_url`: URL to a video of the property (optional)
- `created_at`: Timestamp when the record was created
- `updated_at`: Timestamp when the record was last updated

### Tasks Table

- `id`: Primary key
- `visit_id`: Foreign key referencing the property visit
- `task_type`: Type of task (property_tour, feedback_collection, listing_agent_notification, buyer_followup)
- `status`: Status of the task (scheduled, in_progress, completed, cancelled, failed)
- `scheduled_time`: Scheduled time for the task
- `completed_time`: Time when the task was completed (optional)
- `shipment_id`: ID of the shipment in the Route Optimization API (optional)
- `created_at`: Timestamp when the record was created
- `updated_at`: Timestamp when the record was last updated

### Feedback Table

- `id`: Primary key
- `task_id`: Foreign key referencing the task
- `raw_feedback`: Raw feedback text (optional)
- `processed_feedback`: Processed/summarized feedback text (optional)
- `feedback_source`: Source of the feedback (sms, voice, app, email, manual)
- `timestamp`: Time when the feedback was received
- `sent_to_agent`: Whether the feedback has been sent to the listing agent
- `created_at`: Timestamp when the record was created
- `updated_at`: Timestamp when the record was last updated

## Deployment Notes

- For production, consider deploying to Google Cloud Functions, Google Kubernetes Engine, or Railway
- Switch from uvicorn to gunicorn for better resource allocation in production
- Replace SQLite with a more robust database like PostgreSQL or MongoDB for production
- Ensure proper authentication with Google Cloud services
- Implement real SMS and voice integration for feedback collection
