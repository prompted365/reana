import os
import datetime
import logging
from typing import List, Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
import google.auth
from google.auth.transport.requests import AuthorizedSession

load_dotenv()
app = FastAPI()

# Environment variables and validation
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "YOUR_PROJECT_ID")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    logging.error("Missing GOOGLE_API_KEY environment variable.")
    raise RuntimeError("Missing GOOGLE_API_KEY environment variable.")

logging.basicConfig(level=logging.INFO)

# --- Pydantic models ---
class Property(BaseModel):
    address: str
    available_from: str  # "HH:MM"
    available_to: str    # "HH:MM"
    square_footage: int
    video_url: Optional[str] = None
    sellside_agent_name: str
    contact_method_preferred: str  # e.g. "sms", "call", etc.
    confirmation_status: str
    constraint_indicator: str

class OptimizeRequest(BaseModel):
    agent_home: str
    tour_start_time: str  # ISO formatted string, e.g., "2025-03-03T09:00:00"
    tour_end_time: str    # ISO formatted string, e.g., "2025-03-03T17:00:00"
    properties: List[Property]
    start_preference: Optional[str] = Field("optimize", pattern="^(furthest|closest|optimize)$")

class Appointment(BaseModel):
    property_address: str
    arrival_time: str
    start_visit: str
    end_visit: str
    visit_duration_minutes: int
    video_url: Optional[str] = None

class OptimizeResponse(BaseModel):
    waypoint_order: List[int]
    schedule: List[Appointment]
    total_drive_time_minutes: int
    total_drive_distance_km: float

# --- Utility functions ---
def to_utc_z(dt_str: str) -> str:
    """Convert a datetime string (assumed ISO 8601) to UTC ISO 8601 with a trailing 'Z'."""
    try:
        dt = datetime.datetime.fromisoformat(dt_str)
        # If the datetime is naive, assume it is already in local time (or set a default)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=datetime.timezone.utc)
        # Convert to UTC and format with trailing "Z"
        return dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
    except Exception as e:
        logging.error(f"Error converting datetime to UTC: {e}")
        raise HTTPException(status_code=400, detail="Invalid datetime format. Expected ISO 8601 format.")

def seconds_to_minutes(seconds: int) -> int:
    return (seconds + 59) // 60

def meters_to_km(meters: int) -> float:
    return round(meters / 1000.0, 1)

# --- Asynchronous external API calls ---
async def geocode_address(address: str) -> Optional[dict]:
    """Convert an address to latitude/longitude using the Google Geocoding API."""
    geocode_url = "https://maps.googleapis.com/maps/api/geocode/json"
    params = {"address": address, "key": GOOGLE_API_KEY}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(geocode_url, params=params)
            if response.status_code != 200:
                logging.error(f"Geocoding API error: {response.status_code} {response.text}")
                return None
            data = response.json()
            if data.get("status") != "OK" or not data.get("results"):
                logging.error(f"Geocoding failed for address '{address}': {data.get('status')}")
                return None
            location = data["results"][0]["geometry"]["location"]
            return {"lat": location["lat"], "lng": location["lng"]}
    except Exception as e:
        logging.error(f"Exception during geocoding for '{address}': {e}")
        return None

async def call_route_optimization_api(payload: dict) -> dict:
    """
    Calls the Google Route Optimization API using Application Default Credentials.
    Note: AuthorizedSession is synchronous; here we simulate an async call with httpx.
    """
    try:
        credentials, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        authed_session = AuthorizedSession(credentials)
    except Exception as e:
        logging.error(f"Google authentication failed: {e}")
        raise HTTPException(status_code=500, detail="Google authentication failed.")
    
    route_opt_url = f"https://routeoptimization.googleapis.com/v1/projects/{GCP_PROJECT_ID}:optimizeTours"
    headers = {"Content-Type": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(route_opt_url, json=payload, headers=headers)
            if response.status_code != 200:
                logging.error(f"Route Optimization API error: {response.status_code} {response.text}")
                raise HTTPException(status_code=500, detail="Route Optimization API error.")
            return response.json()
    except Exception as e:
        logging.error(f"Exception calling Route Optimization API: {e}")
        raise HTTPException(status_code=500, detail="Failed to call Route Optimization API.")

# --- FastAPI endpoint ---
@app.post("/optimize", response_model=OptimizeResponse)
async def optimize_tours(opt_req: OptimizeRequest):
    # Convert tour times to UTC ISO 8601 format
    tour_start_utc = to_utc_z(opt_req.tour_start_time)
    tour_end_utc = to_utc_z(opt_req.tour_end_time)
    if tour_start_utc >= tour_end_utc:
        raise HTTPException(status_code=400, detail="Tour end time must be after start time.")

    # Geocode agent home
    agent_coords = await geocode_address(opt_req.agent_home)
    if not agent_coords:
        raise HTTPException(status_code=400, detail="Failed to geocode agent home address.")

    # Geocode each property asynchronously
    property_coords = []
    for prop in opt_req.properties:
        coords = await geocode_address(prop.address)
        if not coords:
            raise HTTPException(status_code=400, detail=f"Failed to geocode property address: {prop.address}")
        property_coords.append(coords)

    # Build payload for route optimization API (this payload is illustrative)
    optimization_payload = {
        "startLocation": {"latitude": agent_coords["lat"], "longitude": agent_coords["lng"]},
        "endLocation": {"latitude": agent_coords["lat"], "longitude": agent_coords["lng"]},
        "globalStartTime": tour_start_utc,
        "globalEndTime": tour_end_utc,
        "properties": [
            {
                "address": prop.address,
                "location": {"latitude": coords["lat"], "longitude": coords["lng"]},
                "availableTimeWindow": {"start": prop.available_from, "end": prop.available_to},
                "squareFootage": prop.square_footage,
            }
            for prop, coords in zip(opt_req.properties, property_coords)
        ],
        "startPreference": opt_req.start_preference,
    }

    logging.info(f"Optimization payload: {optimization_payload}")
    api_response = await call_route_optimization_api(optimization_payload)

    # Parse the API response
    try:
        waypoint_order = api_response.get("waypointOrder", [])
        schedule_raw = api_response.get("schedule", [])
        total_drive_time_seconds = api_response.get("totalDriveTimeSeconds", 0)
        total_drive_distance_meters = api_response.get("totalDriveDistanceMeters", 0)

        schedule = []
        for visit in schedule_raw:
            appointment = Appointment(
                property_address=visit.get("propertyAddress", ""),
                arrival_time=visit.get("arrivalTime", ""),
                start_visit=visit.get("startVisit", ""),
                end_visit=visit.get("endVisit", ""),
                visit_duration_minutes=visit.get("visitDurationMinutes", 0),
                video_url=visit.get("videoUrl"),
            )
            schedule.append(appointment)

        return OptimizeResponse(
            waypoint_order=waypoint_order,
            schedule=schedule,
            total_drive_time_minutes=seconds_to_minutes(total_drive_time_seconds),
            total_drive_distance_km=meters_to_km(total_drive_distance_meters),
        )
    except Exception as e:
        logging.error(f"Error parsing optimization response: {e}")
        raise HTTPException(status_code=500, detail="Failed to parse optimization response.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)