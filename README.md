# REanna Router

A FastAPI application that optimizes real estate tour schedules using Google's Route Optimization API.

## Features

- Optimizes property viewing schedules for real estate agents
- Uses Google Maps APIs for geocoding and route optimization
- Generates HTML schedules with detailed tour information
- Supports different agent preferences (optimize, furthest, closest)

## Prerequisites

- Docker and Docker Compose
- Google Cloud Platform account with the following APIs enabled:
  - Geocoding API
  - Routes API
  - Route Optimization API
- Google Cloud credentials

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

### POST /optimize

Optimizes a real estate tour schedule.

Example request:

```json
{
  "agent_home": "10 Columbus Circle, New York, NY 10019",
  "tour_start_time": "2025-03-03T09:00:00Z",
  "tour_end_time": "2025-03-03T17:00:00Z",
  "properties": [
    {
      "address": "350 5th Ave, New York, NY 10118",
      "available_from": "09:30",
      "available_to": "11:00",
      "square_footage": 1800,
      "video_url": "https://example.com/videos/empire-state.mp4",
      "sellside_agent_name": "Agent A",
      "contact_method_preferred": "sms",
      "confirmation_status": "confirmed",
      "constraint_indicator": "flexible"
    },
    // Additional properties...
  ],
  "start_preference": "optimize"
}
```

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

## Deployment Notes

- For production, consider deploying to Google Cloud Functions, Google Kubernetes Engine, or Railway
- Switch from uvicorn to gunicorn for better resource allocation in production
- Ensure proper authentication with Google Cloud services

## Benchmark

Run with

```bash
chmod +x benchmark.sh
./benchmark.sh
```
