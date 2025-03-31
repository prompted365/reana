import os
import datetime
import logging
import json
from typing import List, Dict, Any, Tuple, Optional

import google.auth
from google.auth.transport.requests import AuthorizedSession, Request
import requests

from app.models import (
    Tour, PropertyVisit, PropertyVisitCreate, Task, TaskCreate,
    create_property_visit, create_property_tour_task, update_task,
    get_property_visit, get_tasks_by_visit, update_property_visit
)
from app.utils.time_utils import to_utc_z, from_utc_z, seconds_to_minutes, meters_to_kilometers

# Required by Route Optimization API:
GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID", "YOUR_PROJECT_ID")
# For Geocoding only:
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

logging.basicConfig(level=logging.INFO)

def geocode_address(address: str) -> Dict[str, float]:
    """
    Convert address to lat/lng using the Geocoding API.
    """
    if not GOOGLE_API_KEY:
        raise ValueError("Missing Geocoding API key.")
    
    params = {"address": address, "key": GOOGLE_API_KEY}
    url = "https://maps.googleapis.com/maps/api/geocode/json"
    resp = requests.get(url, params=params, timeout=10)
    data = resp.json()
    
    if data.get("status") != "OK":
        logging.error(f"Geocoding failed for '{address}': {data}")
        raise ValueError(f"Geocoding failed for '{address}'")
    
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

def map_properties_to_shipments(
    tour: Tour,
    properties: List[Dict[str, Any]],
    agent_coords: Dict[str, float]
) -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Maps property visits to shipments for the Route Optimization API.
    Returns the request body and a mapping of shipment labels to visit IDs.
    """
    # Parse tour start and end times
    tour_start = datetime.datetime.fromisoformat(tour.start_time)
    tour_end = datetime.datetime.fromisoformat(tour.end_time)
    
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
    
    # Build shipments and track the mapping of shipment labels to visit IDs
    shipments = []
    shipment_to_visit_map = {}
    
    for i, prop in enumerate(properties):
        # Create a property visit record
        date_part = tour_start.date()
        from_time = datetime.datetime.strptime(prop["available_from"], "%H:%M").time()
        to_time = datetime.datetime.strptime(prop["available_to"], "%H:%M").time()
        window_start = datetime.datetime.combine(date_part, from_time)
        window_end = datetime.datetime.combine(date_part, to_time)
        
        # Create a property visit in the database
        visit = PropertyVisitCreate(
            tour_id=tour.id,
            address=prop["address"],
            property_id=f"prop_{i}",
            scheduled_arrival=window_start.isoformat(),
            scheduled_departure=window_end.isoformat(),
            status="scheduled",
            sellside_agent_name=prop.get("sellside_agent_name"),
            contact_method=prop.get("contact_method_preferred"),
            confirmation_status=prop.get("confirmation_status"),
            constraint_indicator=prop.get("constraint_indicator"),
            square_footage=prop.get("square_footage", 1500),
            video_url=prop.get("video_url")
        )
        
        created_visit = create_property_visit(visit)
        
        # Create a property tour task
        task = create_property_tour_task(
            visit_id=created_visit.id,
            scheduled_time=window_start.isoformat()
        )
        
        # Get coordinates for the property
        coords = geocode_address(prop["address"])
        
        # Create a shipment for this property visit
        shipment_label = f"Property_{i}_{created_visit.id}"
        shipment = {
            "label": shipment_label,
            "pickups": [
                {
                    "arrival_location": {
                        "latitude": coords["lat"],
                        "longitude": coords["lng"]
                    },
                    "duration": compute_visit_duration_seconds(prop.get("square_footage", 1500)),
                    "time_windows": [
                        {
                            "start_time": to_utc_z(window_start),
                            "end_time": to_utc_z(window_end)
                        }
                    ]
                }
            ]
        }
        
        shipments.append(shipment)
        shipment_to_visit_map[shipment_label] = created_visit.id
        
        # Update the task with the shipment ID
        update_task(task.id, {"shipment_id": shipment_label})
    
    # Build the complete request body
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
    
    return request_body, shipment_to_visit_map

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
        raise ValueError(f"Route Optimization API error: {resp.text}")
    
    response_data = resp.json()
    logging.info(f"Route Optimization API response: {response_data}")
    return response_data

def parse_optimization_response(
    api_response: Dict[str, Any],
    shipment_to_visit_map: Dict[str, str]
) -> Dict[str, Any]:
    """
    Parse the Route Optimization API response and update the database.
    Returns a structured response with the optimized schedule.
    """
    logging.info("Parsing optimization response...")
    
    # Initialize result structure
    result = {
        "waypoint_order": [],
        "schedule": [],
        "total_drive_time_minutes": 0,
        "total_drive_distance_km": 0.0
    }
    
    # Check if we have a valid response with routes
    if not api_response.get("routes"):
        logging.warning("No routes found in optimization response")
        return result
    
    # We'll use the first route (should only be one since we only have one vehicle)
    route = api_response["routes"][0]
    
    # Extract visits and transitions
    visits = route.get("visits", [])
    transitions = route.get("transitions", [])
    
    # Process each visit to create appointments
    property_visits = []
    total_drive_time_seconds = 0
    total_drive_distance_meters = 0
    
    for i, visit in enumerate(visits):
        shipment_label = visit.get("shipmentLabel", "")
        if not shipment_label or shipment_label not in shipment_to_visit_map:
            continue
        
        visit_id = shipment_to_visit_map[shipment_label]
        property_visit = get_property_visit(visit_id)
        if not property_visit:
            logging.error(f"Property visit not found for shipment {shipment_label}")
            continue
        
        # Extract times from the visit
        arrival_time = visit.get("startTime", "")
        if not arrival_time:
            continue
        
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
        
        # Parse arrival time
        arrival_dt = from_utc_z(arrival_time)
        
        # Calculate end time based on duration
        duration_minutes = compute_visit_duration_minutes(property_visit.square_footage or 1500)
        end_dt = arrival_dt + datetime.timedelta(minutes=duration_minutes)
        end_time = to_utc_z(end_dt)
        
        # Update the property visit with the scheduled times
        update_property_visit(
            visit_id,
            {
                "scheduled_arrival": arrival_dt.isoformat(),
                "scheduled_departure": end_dt.isoformat()
            }
        )
        
        # Add to the result
        appointment = {
            "property_address": property_visit.address,
            "arrival_time": arrival_time,
            "start_visit": arrival_time,
            "end_visit": end_time,
            "visit_duration_minutes": duration_minutes,
            "video_url": property_visit.video_url,
            "drive_time_minutes": drive_time_minutes,
            "drive_distance_km": drive_distance_km,
            "sellside_agent_name": property_visit.sellside_agent_name,
            "contact_method_preferred": property_visit.contact_method,
            "confirmation_status": property_visit.confirmation_status,
            "constraint_indicator": property_visit.constraint_indicator
        }
        
        result["schedule"].append(appointment)
        result["waypoint_order"].append(int(property_visit.property_id.split("_")[1]))
        
        # Update the task with the scheduled time
        tasks = get_tasks_by_visit(visit_id)
        for task in tasks:
            if task.task_type == "property_tour":
                update_task(task.id, {"scheduled_time": arrival_dt.isoformat()})
    
    # Sort schedule by arrival time
    result["schedule"].sort(key=lambda x: x["arrival_time"])
    
    # Calculate total drive time and distance
    result["total_drive_time_minutes"] = seconds_to_minutes(total_drive_time_seconds)
    result["total_drive_distance_km"] = meters_to_kilometers(total_drive_distance_meters)
    
    # If we have metrics in the response, use those instead
    if "metrics" in route:
        metrics = route["metrics"]
        if "travelDuration" in metrics:
            travel_duration = metrics["travelDuration"]
            if isinstance(travel_duration, str) and travel_duration.endswith("s"):
                total_drive_time_seconds = int(travel_duration.rstrip("s"))
                result["total_drive_time_minutes"] = seconds_to_minutes(total_drive_time_seconds)
        
        if "travelDistanceMeters" in metrics:
            total_drive_distance_meters = float(metrics["travelDistanceMeters"])
            result["total_drive_distance_km"] = meters_to_kilometers(total_drive_distance_meters)
    
    return result

def optimize_tour(
    tour: Tour,
    properties: List[Dict[str, Any]],
    agent_home: str
) -> Dict[str, Any]:
    """
    Optimize a tour schedule using the Google Route Optimization API.
    """
    # Geocode agent home
    agent_coords = geocode_address(agent_home)
    
    # Map properties to shipments
    request_body, shipment_to_visit_map = map_properties_to_shipments(tour, properties, agent_coords)
    
    # Call the optimization API
    api_response = call_route_optimization_api(request_body)
    
    # Parse the response
    result = parse_optimization_response(api_response, shipment_to_visit_map)
    
    return result

# Add the missing OptimizationService class that's imported by the routes
class OptimizationService:
    """
    Service for optimizing tour routes and schedules.
    This class acts as a wrapper around the optimization functions.
    """
    
    def __init__(self, db):
        """
        Initialize the optimization service
        
        Args:
            db: Database connection
        """
        self.db = db
        
    async def create_and_optimize_tour(self, agent_id: str, property_addresses: List[str], 
                                      start_time: str, strategy: str = "optimal") -> Tour:
        """
        Create a new tour and optimize the route
        
        Args:
            agent_id: ID of the agent
            property_addresses: List of property addresses to visit
            start_time: Start time of the tour (ISO format)
            strategy: Optimization strategy (optimal, nearest, etc.)
            
        Returns:
            Tour: Created tour with optimized schedule
        """
        # Create basic properties list for optimization
        properties = []
        for i, address in enumerate(property_addresses):
            # Determine availability window (simple example)
            # In a real app, this would be based on property availability data
            # Here we're setting a 2-hour window from the tour start time
            from datetime import datetime, timedelta
            start_dt = datetime.fromisoformat(start_time)
            end_dt = start_dt + timedelta(hours=2)
            
            properties.append({
                "address": address,
                "available_from": start_dt.strftime("%H:%M"),
                "available_to": end_dt.strftime("%H:%M"),
                "square_footage": 1500  # Default value
            })
        
        # Create tour in database
        tour = await self.db.create_tour(agent_id, start_time)
        
        # Optimize the tour using the standalone function
        result = optimize_tour(tour, properties, agent_id)
        return tour
