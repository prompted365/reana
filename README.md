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

## Database

REanna Router uses SQLite for development, but can be configured to use other databases for production. The database schema includes tables for:

- Tours
- Property Visits
- Tasks
- Feedback

## Deployment Notes

- For production, consider deploying to Google Cloud Functions, Google Kubernetes Engine, or Railway
- Switch from uvicorn to gunicorn for better resource allocation in production
- Replace SQLite with a more robust database like PostgreSQL or MongoDB for production
- Ensure proper authentication with Google Cloud services
- Implement real SMS and voice integration for feedback collection
