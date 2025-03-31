# REanna Router - Developer Guide

This guide provides practical information for developers working with the REanna Router system. It includes setup instructions, API usage examples, guidance for extending the system, and best practices.

## 1. Development Environment Setup

### 1.1 Prerequisites

- Python 3.9+
- Git
- Docker (optional, for containerized development)
- Google Cloud account with access to:
  - Geocoding API
  - Route Optimization API
  - Routes API

### 1.2 Initial Setup

Clone the repository and set up the development environment:

```bash
# Clone the repository
git clone [repository-url]
cd reanna_router

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 1.3 Google Cloud Setup

Run the included setup script to configure Google Cloud authentication:

```bash
# Make the script executable
chmod +x setup_gcp_credentials.sh

# Run the setup script
./setup_gcp_credentials.sh
```

Alternatively, you can manually set up credentials:

```bash
# Option 1: Use a service account key
# Download the service account key as google-credentials.json
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/google-credentials.json"

# Option 2: Use application default credentials
gcloud auth application-default login
export GOOGLE_APPLICATION_CREDENTIALS=~/.config/gcloud/application_default_credentials.json
```

### 1.4 Environment Variables

Create a `.env` file with the following variables:

```
GOOGLE_API_KEY=your_google_api_key
GCP_PROJECT_ID=your_gcp_project_id
GOOGLE_APPLICATION_CREDENTIALS=/path/to/your/google-credentials.json
```

### 1.5 Database Initialization

The database will be automatically initialized when you run the application. If you need to reset the database, you can delete the `reanna_router.db` file and it will be recreated when you restart the application.

### 1.6 Running the Application

```bash
# Run the application
python main.py

# Alternatively, you can use uvicorn directly
uvicorn app.main:app --reload
```

The API will be available at <http://localhost:8000>.

### 1.7 Docker Development

Build and run the application with Docker:

```bash
# Build the image
docker build -t reanna-router .

# Run the container
docker run -p 8000:8000 -v $(pwd)/google-credentials.json:/app/google-credentials.json -e GOOGLE_APPLICATION_CREDENTIALS=/app/google-credentials.json reanna-router
```

## 2. API Usage Examples

### 2.1 Create a Tour

```python
import requests
import json

# Define the properties for the tour
properties = [
    {
        "address": "123 Main St, Anytown, USA",
        "square_footage": 1800,
        "available_from": "09:00",
        "available_to": "17:00",
        "sellside_agent_name": "Jane Smith",
        "contact_method_preferred": "email"
    },
    {
        "address": "456 Oak Ave, Anytown, USA",
        "square_footage": 2200,
        "available_from": "10:00",
        "available_to": "16:00",
        "sellside_agent_name": "John Doe",
        "contact_method_preferred": "sms"
    },
    {
        "address": "789 Pine Rd, Anytown, USA",
        "square_footage": 1500,
        "available_from": "09:30",
        "available_to": "15:30",
        "sellside_agent_name": "Emily Johnson",
        "contact_method_preferred": "email"
    }
]

# Create a tour
response = requests.post(
    "http://localhost:8000/tours/",
    params={
        "agent_id": "agent123",
        "start_time": "2025-04-15T09:00:00",
        "end_time": "2025-04-15T17:00:00",
        "agent_home": "100 Center St, Anytown, USA"
    },
    json=properties
)

# Parse the response
result = response.json()
tour_id = result["tour_id"]
schedule = result["optimization_result"]["schedule"]

print(f"Tour created with ID: {tour_id}")
print(f"Optimized schedule: {json.dumps(schedule, indent=2)}")
```

### 2.2 Get Tour Details

```python
import requests

# Get tour details
response = requests.get(f"http://localhost:8000/tours/{tour_id}")
tour_details = response.json()

print(f"Tour details: {json.dumps(tour_details, indent=2)}")
```

### 2.3 Record Property Visit Progress

```python
import requests
import datetime

# Record arrival at a property
visit_id = "property_visit_id"  # Replace with actual visit ID
response = requests.put(
    f"http://localhost:8000/property-visits/{visit_id}/arrival",
    params={"arrival_time": datetime.datetime.now().isoformat()}
)
arrival_result = response.json()

print(f"Arrival recorded: {json.dumps(arrival_result, indent=2)}")

# ... after the visit ...

# Record departure from the property
response = requests.put(
    f"http://localhost:8000/property-visits/{visit_id}/departure",
    params={"departure_time": datetime.datetime.now().isoformat()}
)
departure_result = response.json()

print(f"Departure recorded: {json.dumps(departure_result, indent=2)}")
```

### 2.4 Submit Feedback

```python
import requests

# Submit SMS feedback
task_id = "feedback_task_id"  # Replace with actual task ID
response = requests.post(
    "http://localhost:8000/feedback/sms",
    params={
        "task_id": task_id,
        "feedback_text": "The property was nice but smaller than expected. The kitchen needs updating, but the location is excellent."
    }
)
feedback_result = response.json()

print(f"Feedback submitted: {json.dumps(feedback_result, indent=2)}")
```

### 2.5 Get Tour Journal

```python
import requests

# Get the tour journal
response = requests.get(f"http://localhost:8000/tours/{tour_id}/journal")
journal = response.json()

print(f"Tour journal: {json.dumps(journal, indent=2)}")
```

### 2.6 Testing With cURL

You can also use cURL to test the API:

```bash
# Create a tour
curl -X POST "http://localhost:8000/tours/?agent_id=agent123&start_time=2025-04-15T09:00:00&end_time=2025-04-15T17:00:00&agent_home=100%20Center%20St%2C%20Anytown%2C%20USA" \
  -H "Content-Type: application/json" \
  -d '[{"address":"123 Main St, Anytown, USA","square_footage":1800,"available_from":"09:00","available_to":"17:00"}]'

# Get tour details
curl -X GET "http://localhost:8000/tours/{tour_id}"
```

## 3. Extending the System

### 3.1 Adding a New API Endpoint

To add a new API endpoint, follow these steps:

1. Identify the appropriate router file in `app/api/routes/`
2. Add your endpoint with the correct HTTP method and path:

```python
@router.get("/custom-endpoint", response_model=Dict[str, Any])
async def custom_endpoint(param1: str, param2: Optional[int] = None):
    """
    Documentation for your endpoint.
    """
    # Your implementation here
    return {"result": "success", "data": {...}}
```

3. If you're creating a new router file, register it in `app/main.py`:

```python
from app.api.routes import your_new_router

app.include_router(your_new_router)
```

### 3.2 Adding a New Model

To add a new data model, follow these steps:

1. Create a new file in `app/models/` (e.g., `app/models/new_model.py`)
2. Define your Pydantic models:

```python
from pydantic import BaseModel
from typing import Optional, List

class NewModelBase(BaseModel):
    name: str
    description: Optional[str]
    related_field: str

class NewModelCreate(NewModelBase):
    pass

class NewModel(NewModelBase):
    id: str
    created_at: str
    updated_at: str
```

3. Define your database functions:

```python
from app.models.database import get_db_connection, generate_id, current_timestamp

def create_new_model(model: NewModelCreate) -> NewModel:
    """Create a new instance in the database."""
    model_id = generate_id()
    now = current_timestamp()
    
    with get_db_connection() as conn:
        conn.execute(
            """
            INSERT INTO new_models (id, name, description, related_field, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (model_id, model.name, model.description, model.related_field, now, now)
        )
        conn.commit()
    
    return NewModel(
        id=model_id,
        name=model.name,
        description=model.description,
        related_field=model.related_field,
        created_at=now,
        updated_at=now
    )

# Add other CRUD functions as needed
```

4. Add the database table to `init_db()` in `app/models/database.py`:

```python
def init_db():
    """Initialize the database with required tables."""
    with get_db_connection() as conn:
        # ... existing tables ...
        
        # Create new_models table
        conn.execute('''
        CREATE TABLE IF NOT EXISTS new_models (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            related_field TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        conn.commit()
```

### 3.3 Adding a New Service

To add a new service, follow these steps:

1. Create a new file in `app/services/` (e.g., `app/services/new_service.py`)
2. Implement your service functions:

```python
import logging
from typing import Dict, Any, List, Optional

from app.models import NewModel, get_new_model, update_new_model

logging.basicConfig(level=logging.INFO)

async def process_new_model(model_id: str) -> Dict[str, Any]:
    """
    Process a new model.
    """
    model = get_new_model(model_id)
    if not model:
        logging.error(f"Model not found: {model_id}")
        return {"error": "Model not found"}
    
    # Your processing logic here
    result = {"processed": True, "model_id": model_id}
    
    # Update the model with the processing result
    update_new_model(model_id, {"processed": True})
    
    return result
```

3. Import and use your service in the appropriate router:

```python
from app.services.new_service import process_new_model

@router.post("/process/{model_id}", response_model=Dict[str, Any])
async def process_model_endpoint(model_id: str):
    """
    Process a model.
    """
    result = await process_new_model(model_id)
    return result
```

### 3.4 Integrating with External Services

To integrate with external services (like SMS or voice services for feedback), follow these steps:

1. Add the necessary dependencies to `requirements.txt`
2. Create a utility file for the integration in `app/utils/`
3. Implement the integration functions
4. Use the integration in your service

Example for integrating with an SMS service:

```python
# app/utils/sms_service.py
import requests
import logging
from typing import Dict, Any

SMS_API_KEY = os.getenv("SMS_API_KEY")
SMS_API_URL = "https://api.smsservice.com/send"

def send_sms(phone_number: str, message: str) -> Dict[str, Any]:
    """
    Send an SMS using the external SMS service.
    """
    if not SMS_API_KEY:
        logging.error("SMS API key not configured")
        return {"error": "SMS API key not configured"}
    
    payload = {
        "api_key": SMS_API_KEY,
        "phone": phone_number,
        "message": message
    }
    
    response = requests.post(SMS_API_URL, json=payload, timeout=10)
    if response.status_code != 200:
        logging.error(f"SMS API error: {response.text}")
        return {"error": f"SMS API error: {response.status_code}"}
    
    return response.json()
```

Then use it in your service:

```python
from app.utils.sms_service import send_sms

async def notify_agent_via_sms(agent_phone: str, feedback: str) -> Dict[str, Any]:
    """
    Notify an agent about feedback via SMS.
    """
    message = f"New feedback received: {feedback}"
    return send_sms(agent_phone, message)
```

## 4. Common Issues and Debugging

### 4.1 Google Cloud Authentication Issues

If you encounter authentication issues with Google Cloud APIs:

1. Verify the environment variable is set correctly:

   ```bash
   echo $GOOGLE_APPLICATION_CREDENTIALS
   ```

2. Check that the service account has the necessary permissions:
   - `roles/maps.routeOptimizer`
   - `roles/maps.routesUser`
   - `roles/maps.viewer`

3. Verify API enablement in Google Cloud Console:
   - Geocoding API
   - Route Optimization API
   - Routes API

4. Check for expired credentials:

   ```bash
   gcloud auth application-default print-access-token
   ```

### 4.2 Database Issues

If you encounter database issues:

1. Check that the database file exists and has the correct permissions:

   ```bash
   ls -la reanna_router.db
   ```

2. Reset the database if needed:

   ```bash
   rm reanna_router.db
   python -c "from app.models.database import init_db; init_db()"
   ```

3. Verify SQLite installation:

   ```bash
   sqlite3 --version
   ```

### 4.3 API Endpoint Issues

If API endpoints are not working as expected:

1. Check the API documentation at <http://localhost:8000/docs>
2. Verify the request format using the examples in the documentation
3. Check the server logs for error messages
4. Use debug logging for more detailed information:

   ```python
   import logging
   logging.basicConfig(level=logging.DEBUG)
   ```

### 4.4 Route Optimization Issues

If the route optimization is not working as expected:

1. Verify that all addresses can be geocoded:

   ```python
   from app.services.optimization_service import geocode_address
   
   coords = geocode_address("123 Main St, Anytown, USA")
   print(coords)
   ```

2. Check the time windows for each property:
   - Ensure start time is before end time
   - Ensure all times are in the correct format (HH:MM)
   - Ensure all times are within the tour start and end times

3. Verify the optimization API response:

   ```python
   import logging
   logging.getLogger("app.services.optimization_service").setLevel(logging.DEBUG)
   ```

### 4.5 Running Tests

Run the included test script to verify the system is working correctly:

```bash
python test.py
```

## 5. Best Practices

### 5.1 Code Style and Organization

- Follow PEP 8 guidelines for Python code style
- Use consistent naming conventions:
  - snake_case for variables and functions
  - CamelCase for classes
  - ALL_CAPS for constants
- Organize imports alphabetically and by category (standard library, third-party, local)
- Include docstrings for all functions, classes, and modules
- Use type hints consistently

### 5.2 API Design

- Use descriptive names for endpoints and parameters
- Use standard HTTP methods appropriately:
  - GET for retrieving data
  - POST for creating resources
  - PUT for updating resources
  - DELETE for removing resources
- Include comprehensive error handling
- Return appropriate HTTP status codes
- Document all endpoints with clear descriptions and examples

### 5.3 Database Operations

- Use the context manager pattern for database connections
- Always use parameterized queries to prevent SQL injection
- Keep database operations encapsulated in model functions
- Include appropriate error handling for database operations
- Use transactions for operations that modify multiple records

### 5.4 Asynchronous Programming

- Use async/await consistently in FastAPI routes
- Be mindful of blocking operations in async functions
- Use asyncio.gather() for parallel operations
- Handle exceptions properly in async functions
- Use asyncio.create_task() for background tasks

### 5.5 Testing

- Write unit tests for all functions
- Include integration tests for key workflows
- Use pytest for test organization and execution
- Mock external dependencies in tests
- Include edge cases and error conditions in tests

### 5.6 Security

- Validate all input data
- Use HTTPS in production
- Store sensitive credentials in environment variables
- Implement proper authentication and authorization
- Limit the information exposed in error messages

## 6. Example Workflows

### 6.1 Full Tour Lifecycle Example

Here's a complete workflow example that demonstrates creating a tour, recording property visits, and collecting feedback:

```python
import requests
import time
import json
from datetime import datetime, timedelta

# Base URL for the API
BASE_URL = "http://localhost:8000"

# 1. Create a tour
properties = [
    {
        "address": "123 Main St, Anytown, USA",
        "square_footage": 1800,
        "available_from": "09:00",
        "available_to": "17:00",
        "sellside_agent_name": "Jane Smith",
        "contact_method_preferred": "email"
    },
    {
        "address": "456 Oak Ave, Anytown, USA",
        "square_footage": 2200,
        "available_from": "10:00",
        "available_to": "16:00",
        "sellside_agent_name": "John Doe",
        "contact_method_preferred": "sms"
    }
]

response = requests.post(
    f"{BASE_URL}/tours/",
    params={
        "agent_id": "agent123",
        "start_time": "2025-04-15T09:00:00",
        "end_time": "2025-04-15T17:00:00",
        "agent_home": "100 Center St, Anytown, USA"
    },
    json=properties
)

result = response.json()
tour_id = result["tour_id"]
print(f"Tour created with ID: {tour_id}")

# 2. Get the tour details
response = requests.get(f"{BASE_URL}/tours/{tour_id}")
tour_details = response.json()
print(f"Tour details retrieved")

# Get the first property visit
first_visit = tour_details["property_visits"][0]
visit_id = first_visit["visit_id"]
print(f"First property visit ID: {visit_id}")

# 3. Update the tour status to in_progress
response = requests.put(
    f"{BASE_URL}/tours/{tour_id}/status",
    params={"status": "in_progress"}
)
print(f"Tour status updated to in_progress")

# 4. Record arrival at the first property
response = requests.put(
    f"{BASE_URL}/property-visits/{visit_id}/arrival"
)
print(f"Arrival recorded at first property")

# 5. Find the property tour task
response = requests.get(
    f"{BASE_URL}/tasks/",
    params={"visit_id": visit_id}
)
tasks = response.json()
tour_task = next((task for task in tasks if task["task_type"] == "property_tour"), None)
tour_task_id = tour_task["task_id"]
print(f"Property tour task ID: {tour_task_id}")

# 6. Complete the property tour task
response = requests.put(
    f"{BASE_URL}/tasks/{tour_task_id}/status",
    params={"status": "completed"}
)
print(f"Property tour task completed")

# 7. Record departure from the property
response = requests.put(
    f"{BASE_URL}/property-visits/{visit_id}/departure"
)
print(f"Departure recorded from first property")

# 8. Find the feedback task that was automatically created
time.sleep(1)  # Wait for the feedback task to be created
response = requests.get(
    f"{BASE_URL}/tasks/",
    params={"visit_id": visit_id}
)
tasks = response.json()
feedback_task = next((task for task in tasks if task["task_type"] == "feedback_collection"), None)
feedback_task_id = feedback_task["task_id"]
print(f"Feedback task ID: {feedback_task_id}")

# 9. Submit additional feedback
response = requests.post(
    f"{BASE_URL}/feedback/sms",
    params={
        "task_id": feedback_task_id,
        "feedback_text": "The property was beautiful with lots of natural light. The backyard was smaller than expected, but the interior layout was perfect for our needs."
    }
)
print(f"Additional feedback submitted")

# 10. Complete the tour
response = requests.put(
    f"{BASE_URL}/tours/{tour_id}/status",
    params={"status": "completed"}
)
print(f"Tour completed")

# 11. Get the tour journal
response = requests.get(f"{BASE_URL}/tours/{tour_id}/journal")
journal = response.json()
print(f"Tour journal retrieved with {len(journal['journal_entries'])} entries")
```

## 7. Further Reading

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Google Cloud Fleet Routing API](https://cloud.google.com/optimization)
- [SQLite Documentation](https://www.sqlite.org/docs.html)
- [Pydantic Documentation](https://docs.pydantic.dev/)
- [asyncio Documentation](https://docs.python.org/3/library/asyncio.html)
