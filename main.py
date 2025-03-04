import os
import datetime
import logging
from typing import List, Dict, Any, Tuple, Optional

import requests
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from google.auth.transport.requests import Request
import google.auth
from google.auth.transport.requests import AuthorizedSession

load_dotenv()
app = FastAPI()

# Required by Route Optimization API:
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "YOUR_PROJECT_ID")
# For Geocoding only:
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

logging.basicConfig(level=logging.INFO)

# --- Pydantic models (for our FastAPI endpoint input/output) ---
class Property(BaseModel):
    address: str
    available_from: str  # "HH:MM"
    available_to: str    # "HH:MM"
    square_footage: int
    video_url: Optional[str] = None  # Optional video URL for the property
    sellside_agent_name: str
    contact_method_preferred: str  # "sms", "call", "showingsTime", or "go-direct"
    confirmation_status: str
    constraint_indicator: str

class OptimizeRequest(BaseModel):
    agent_home: str
    tour_start_time: str
    tour_end_time: str
    properties: List[Property]
    start_preference: Optional[str] = "optimize"  # "furthest", "closest", or "optimize"

class Appointment(BaseModel):
    property_address: str
    arrival_time: str
    start_visit: str
    end_visit: str
    visit_duration_minutes: int
    video_url: Optional[str] = None  # Video URL for the property
    drive_time_minutes: Optional[int] = None  # Drive time to this property from previous location
    drive_distance_km: Optional[float] = None  # Drive distance to this property from previous location
    sellside_agent_name: str
    contact_method_preferred: str  # "sms", "call", "showingsTime", or "go-direct"
    confirmation_status: str
    constraint_indicator: str

class OptimizeResponse(BaseModel):
    waypoint_order: List[int]
    schedule: List[Appointment]
    total_drive_time_minutes: int  # Total drive time for the entire tour
    total_drive_distance_km: float  # Total drive distance for the entire tour

def get_route_info(origin: str, destination: str) -> Tuple[int, float]:
    """
    Get accurate travel time and distance between two locations using the Routes API.
    Returns (travel_time_minutes, travel_distance_km)
    """
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not creds.valid:
        creds.refresh(Request())
    authed_session = AuthorizedSession(creds)
    
    url = "https://routes.googleapis.com/directions/v2:computeRoutes"
    
    body = {
        "origin": {
            "address": origin
        },
        "destination": {
            "address": destination
        },
        "travelMode": "DRIVE",
        "routingPreference": "TRAFFIC_AWARE",
        "computeAlternativeRoutes": False,
        "routeModifiers": {
            "avoidTolls": False,
            "avoidHighways": False,
            "avoidFerries": False
        },
        "languageCode": "en-US",
        "units": "METRIC"
    }
    
    headers = {
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters",
        "X-Goog-Api-Key": GOOGLE_API_KEY
    }
    
    resp = authed_session.post(url, json=body, headers=headers, timeout=10)
    if not resp.ok:
        logging.error(f"Routes API error: {resp.text}")
        raise HTTPException(status_code=502, detail=resp.text)
    
    data = resp.json()
    if not data.get("routes"):
        return None, None
        
    route = data["routes"][0]
    travel_time_seconds = int(route["duration"].rstrip("s"))
    travel_time_minutes = seconds_to_minutes(travel_time_seconds)
    travel_distance_meters = float(route["distanceMeters"])
    travel_distance_km = meters_to_kilometers(travel_distance_meters)
    
    return travel_time_minutes, travel_distance_km

def geocode_address(address: str) -> Dict[str, float]:
    """
    Convert address to lat/lng using the Geocoding API.
    """
    if not GOOGLE_API_KEY:
        raise HTTPException(status_code=500, detail="Missing Geocoding API key.")
    
    params = {"address": address, "key": GOOGLE_API_KEY}
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    
    if data.get("status") != "OK":
        logging.error(f"Geocoding failed for '{address}': {data}")
        raise HTTPException(status_code=400, detail=f"Geocoding failed for '{address}'")
    
    loc = data["results"][0]["geometry"]["location"]
    return {"lat": loc["lat"], "lng": loc["lng"]}

def compute_visit_duration_seconds(sq_ft: int) -> str:
    """
    Computes the visit duration based on property square footage.
    Returns a string in Protobuf Duration format (e.g. "900s").
    """
    base_min = 15
    if sq_ft > 1500:
        extra = (sq_ft - 1500) // 500
        base_min += extra * 5
    return f"{base_min * 60}s"

def compute_visit_duration_minutes(sq_ft: int) -> int:
    """
    Computes the visit duration based on property square footage.
    Returns the duration in minutes.
    """
    base_min = 15
    if sq_ft > 1500:
        extra = (sq_ft - 1500) // 500
        base_min += extra * 5
    return base_min

def to_utc_z(dt: datetime.datetime) -> str:
    """
    Convert a naive datetime to UTC ISO 8601 format with a trailing "Z".
    Example: "2025-03-03T13:00:00Z"
    """
    return dt.replace(tzinfo=datetime.timezone.utc).isoformat().replace("+00:00", "Z")

def from_utc_z(utc_str: str) -> datetime.datetime:
    """
    Convert a UTC ISO 8601 string with a trailing "Z" to a datetime object.
    Example: "2025-03-03T13:00:00Z" -> datetime(2025, 3, 3, 13, 0, 0, tzinfo=UTC)
    """
    if utc_str.endswith("Z"):
        utc_str = utc_str[:-1] + "+00:00"
    return datetime.datetime.fromisoformat(utc_str)

def seconds_to_minutes(seconds: int) -> int:
    """
    Convert seconds to minutes, rounding up to the nearest minute.
    """
    return (seconds + 59) // 60  # Round up

def meters_to_kilometers(meters: float) -> float:
    """
    Convert meters to kilometers, rounding to 1 decimal place.
    """
    return round(meters / 1000, 1)

def build_optimize_request_body(
    agent_coords: Dict[str, float],
    tour_start: datetime.datetime,
    tour_end: datetime.datetime,
    properties: List[Property]
) -> Dict[str, Any]:
    """
    Builds a valid OptimizeToursRequest payload for the Route Optimization API.
    """
    # Vehicle definition
    vehicle = {
        "start_location": {
            "latitude": agent_coords["lat"],
            "longitude": agent_coords["lng"]
        },
        "end_location": {
            "latitude": agent_coords["lat"],
            "longitude": agent_coords["lng"]
        },
        "start_time_windows": [
            {
                "start_time": to_utc_z(tour_start),
                "end_time": to_utc_z(tour_end)
            }
        ],
        "end_time_windows": [
            {
                "start_time": to_utc_z(tour_start),
                "end_time": to_utc_z(tour_end)
            }
        ],
        "travel_mode": "DRIVING"
    }

    # Build shipments
    shipments = []
    for i, p in enumerate(properties):
        date_part = tour_start.date()
        from_time = datetime.datetime.strptime(p.available_from, "%H:%M").time()
        to_time = datetime.datetime.strptime(p.available_to, "%H:%M").time()
        window_start = datetime.datetime.combine(date_part, from_time)
        window_end = datetime.datetime.combine(date_part, to_time)
        coords = geocode_address(p.address)
        shipments.append({
            "label": f"Property_{i}",
            "pickups": [
                {
                    "arrival_location": {
                        "latitude": coords["lat"],
                        "longitude": coords["lng"]
                    },
                    "duration": compute_visit_duration_seconds(p.square_footage),
                    "time_windows": [
                        {
                            "start_time": to_utc_z(window_start),
                            "end_time": to_utc_z(window_end)
                        }
                    ]
                }
            ]
        })

    request_body = {
        "timeout": "600s",
        "model": {
            "vehicles": [vehicle],
            "shipments": shipments,
            "global_start_time": to_utc_z(tour_start),
            "global_end_time": to_utc_z(tour_end)
        },
        "consider_road_traffic": True,
        "search_mode": "RETURN_FAST"
    }
    return request_body

def call_route_optimization_api(body: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calls the Google Maps Route Optimization API using ADC.
    """
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if not creds.valid:
        logging.error("Google authentication failed. Refreshing credentials...")
        creds.refresh(Request())
    authed_session = AuthorizedSession(creds)
    url = f"https://routeoptimization.googleapis.com/v1/projects/{GCP_PROJECT_ID}:optimizeTours"
    logging.info("Sending request to Google Route Optimization API...")
    resp = authed_session.post(url, json=body, timeout=60)
    if not resp.ok:
        logging.error(f"Route Optimization API error: {resp.text}")
        raise HTTPException(status_code=502, detail=resp.text)
    
    response_data = resp.json()
    logging.info(f"Route Optimization API response: {response_data}")
    return response_data

def parse_optimization_response(
    api_response: Dict[str, Any], 
    properties: List[Property]
) -> Tuple[List[int], List[Appointment], int, float]:
    """
    Parse the Route Optimization API response into our application's format.
    Returns a tuple of (waypoint_order, schedule, total_drive_time_minutes, total_drive_distance_km).
    """
    logging.info("Parsing optimization response...")
    
    # Initialize empty results
    waypoint_order = []
    schedule = []
    total_drive_time_seconds = 0
    total_drive_distance_meters = 0
    
    # Check if we have a valid response with routes
    if not api_response.get("routes"):
        logging.warning("No routes found in optimization response")
        return [], [], 0, 0.0
    
    # We'll use the first route (should only be one since we only have one vehicle)
    route = api_response["routes"][0]
    logging.info(f"Route data: {route}")
    
    # Extract visits and transitions
    visits = route.get("visits", [])
    transitions = route.get("transitions", [])
    
    # Create a mapping of property indices to their details
    property_map = {}
    for i, visit in enumerate(visits):
        label = visit.get("shipmentLabel", "")
        if not label.startswith("Property_"):
            continue
            
        try:
            property_index = int(label.split("_")[1])
            waypoint_order.append(property_index)
            
            # Store visit details for later use
            property_map[i] = {
                "property_index": property_index,
                "start_time": visit.get("startTime", "")
            }
        except (ValueError, IndexError) as e:
            logging.error(f"Error parsing visit label {label}: {e}")
    
    # Process each visit to create appointments
    for i, visit_info in property_map.items():
        property_index = visit_info["property_index"]
        
        try:
            # Get the property details
            property_data = properties[property_index]
            
            # Extract times from the visit
            arrival_time = visit_info["start_time"]
            start_visit = arrival_time  # In this model, arrival = start of visit
            
            # Calculate end time based on duration
            arrival_dt = from_utc_z(arrival_time)
            duration_minutes = compute_visit_duration_minutes(property_data.square_footage)
            end_dt = arrival_dt + datetime.timedelta(minutes=duration_minutes)
            end_visit = to_utc_z(end_dt)
            
            # Calculate drive time and distance if this isn't the first location
            drive_time_minutes = None
            drive_distance_km = None
            
            # Look for the travel segment that precedes this visit
            if i > 0 and i-1 < len(transitions):
                travel = transitions[i-1]
                if "travelDuration" in travel:
                    drive_time_seconds = int(travel["travelDuration"].rstrip("s"))
                    drive_time_minutes = seconds_to_minutes(drive_time_seconds)
                    total_drive_time_seconds += drive_time_seconds
                
                if "travelDistanceMeters" in travel:
                    drive_distance_meters = float(travel["travelDistanceMeters"])
                    drive_distance_km = meters_to_kilometers(drive_distance_meters)
                    total_drive_distance_meters += drive_distance_meters
            
            # Create appointment with additional fields
            appointment = Appointment(
                property_address=property_data.address,
                arrival_time=arrival_time,
                start_visit=start_visit,
                end_visit=end_visit,
                visit_duration_minutes=duration_minutes,
                video_url=property_data.video_url,
                drive_time_minutes=drive_time_minutes,
                drive_distance_km=drive_distance_km,
                sellside_agent_name=property_data.sellside_agent_name,
                contact_method_preferred=property_data.contact_method_preferred,
                confirmation_status=property_data.confirmation_status,
                constraint_indicator=property_data.constraint_indicator
            )
            schedule.append(appointment)
            
        except (ValueError, IndexError) as e:
            logging.error(f"Error creating appointment for property {property_index}: {e}")
            continue
    
    # Sort schedule by arrival time
    schedule.sort(key=lambda x: x.arrival_time)
    
    # Calculate total drive time and distance
    total_drive_time_minutes = seconds_to_minutes(total_drive_time_seconds)
    total_drive_distance_km = meters_to_kilometers(total_drive_distance_meters)
    
    # If we have metrics in the response, use those instead
    if "metrics" in route:
        metrics = route["metrics"]
        if "travelDuration" in metrics:
            travel_duration = metrics["travelDuration"]
            if isinstance(travel_duration, str) and travel_duration.endswith("s"):
                total_drive_time_seconds = int(travel_duration.rstrip("s"))
                total_drive_time_minutes = seconds_to_minutes(total_drive_time_seconds)
        
        if "travelDistanceMeters" in metrics:
            total_drive_distance_meters = float(metrics["travelDistanceMeters"])
            total_drive_distance_km = meters_to_kilometers(total_drive_distance_meters)
    
    return waypoint_order, schedule, total_drive_time_minutes, total_drive_distance_km

@app.post("/optimize", response_model=OptimizeResponse)
def optimize_schedule(payload: OptimizeRequest):
    """
    FastAPI endpoint to optimize real estate showings.
    """
    # Validate the number of properties
    if len(payload.properties) > 7:
        raise HTTPException(status_code=400, detail="Maximum of 7 properties allowed")
    
    try:
        tour_start = datetime.datetime.fromisoformat(payload.tour_start_time)
        tour_end = datetime.datetime.fromisoformat(payload.tour_end_time)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid time format.")
    if tour_start >= tour_end:
        raise HTTPException(status_code=400, detail="End time must be after start time")
    
    agent_coords = geocode_address(payload.agent_home)
    
    # Handle agent preference for starting furthest or closest to home
    if payload.start_preference in ["furthest", "closest"]:
        logging.info(f"Applying agent preference: {payload.start_preference}")
        # Get distances from agent home to all properties
        distances = []
        for i, p in enumerate(payload.properties):
            try:
                _, distance_km = get_route_info(payload.agent_home, p.address)
                distances.append((i, distance_km if distance_km is not None else 0))
            except Exception as e:
                logging.error(f"Error getting route info: {e}")
                # Use a placeholder distance if API call fails
                distances.append((i, 0))
        
        # Sort properties by distance (ascending or descending)
        if payload.start_preference == "furthest":
            distances.sort(key=lambda x: x[1], reverse=True)  # Furthest first
        else:  # closest
            distances.sort(key=lambda x: x[1])  # Closest first
            
        # Reorder properties based on preference
        ordered_indices = [x[0] for x in distances]
        payload.properties = [payload.properties[i] for i in ordered_indices]
        logging.info(f"Reordered properties based on {payload.start_preference} preference")
    
    body = build_optimize_request_body(agent_coords, tour_start, tour_end, payload.properties)
    
    api_response = call_route_optimization_api(body)
    
    # Parse the response to get the optimized schedule
    waypoint_order, schedule, total_drive_time, total_drive_distance = parse_optimization_response(api_response, payload.properties)
    
    # If we couldn't parse any schedule, return a simple response
    if not schedule:
        logging.warning("No schedule could be parsed from the API response")
        # For testing purposes, create a simple schedule
        total_drive_time = 0
        total_drive_distance = 0.0
        prev_location = None
        
        for i, prop in enumerate(payload.properties):
            date_part = tour_start.date()
            from_time = datetime.datetime.strptime(prop.available_from, "%H:%M").time()
            window_start = datetime.datetime.combine(date_part, from_time)
            duration_minutes = compute_visit_duration_minutes(prop.square_footage)
            end_dt = window_start + datetime.timedelta(minutes=duration_minutes)
            
            # Get accurate drive time and distance if not the first location
            drive_time_minutes = None
            drive_distance_km = None
            
            if prev_location:
                try:
                    # Use Routes API to get accurate travel information
                    drive_time_minutes, drive_distance_km = get_route_info(prev_location, prop.address)
                    if drive_time_minutes is not None and drive_distance_km is not None:
                        total_drive_time += drive_time_minutes
                        total_drive_distance += drive_distance_km
                    else:
                        # Fallback if Routes API doesn't return valid data
                        logging.warning(f"Routes API returned None values for {prev_location} to {prop.address}")
                        drive_time_minutes = 30  # Estimated drive time
                        drive_distance_km = 10.0  # Estimated drive distance
                        total_drive_time += drive_time_minutes
                        total_drive_distance += drive_distance_km
                except Exception as e:
                    # Fallback if Routes API call fails
                    logging.error(f"Error getting route info: {e}")
                    drive_time_minutes = 30  # Estimated drive time
                    drive_distance_km = 10.0  # Estimated drive distance
                    total_drive_time += drive_time_minutes
                    total_drive_distance += drive_distance_km
            
            appointment = Appointment(
                property_address=prop.address,
                arrival_time=to_utc_z(window_start),
                start_visit=to_utc_z(window_start),
                end_visit=to_utc_z(end_dt),
                visit_duration_minutes=duration_minutes,
                video_url=prop.video_url,
                drive_time_minutes=drive_time_minutes,
                drive_distance_km=drive_distance_km
            )
            schedule.append(appointment)
            waypoint_order.append(i)
            prev_location = prop.address
    
    return OptimizeResponse(
        waypoint_order=waypoint_order, 
        schedule=schedule,
        total_drive_time_minutes=total_drive_time,
        total_drive_distance_km=total_drive_distance
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
