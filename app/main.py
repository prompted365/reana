import os
import logging
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import (
    tours_router,
    tasks_router,
    feedback_router,
    property_visits_router,
    monitoring_router,
    dashboard_router
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="REanna Router",
    description="A FastAPI application that optimizes real estate tour schedules using Google's Route Optimization API.",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development; restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(tours_router)
app.include_router(tasks_router)
app.include_router(feedback_router)
app.include_router(property_visits_router)
app.include_router(monitoring_router)
app.include_router(dashboard_router)

# Mount static files directory
static_dir = Path(__file__).resolve().parent / "static"
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@app.get("/")
async def root():
    """
    Root endpoint that returns basic API information.
    """
    return {
        "name": "REanna Router API",
        "version": "1.0.0",
        "description": "Optimizes real estate tour schedules using Google's Route Optimization API.",
        "endpoints": [
            "/tours",
            "/tasks",
            "/feedback",
            "/property-visits",
            "/api/monitoring",
            "/dashboard"
        ]
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy"}

# Backward compatibility with the original API
@app.post("/optimize")
async def optimize_legacy(payload: dict):
    """
    Legacy endpoint for backward compatibility with the original API.
    """
    try:
        # Extract data from the legacy payload
        agent_id = "legacy_agent"  # Default agent ID for legacy requests
        agent_home = payload.get("agent_home", "")
        start_time = payload.get("tour_start_time", "")
        end_time = payload.get("tour_end_time", "")
        properties = payload.get("properties", [])
        
        # Create a tour
        from app.models import TourCreate, create_tour
        tour = TourCreate(
            agent_id=agent_id,
            start_time=start_time,
            end_time=end_time,
            status="scheduled"
        )
        
        created_tour = create_tour(tour)
        
        # Optimize the tour
        from app.services import optimize_tour
        optimization_result = optimize_tour(created_tour, properties, agent_home)
        
        # Update the tour with the route data
        from app.models import update_tour
        update_tour(created_tour.id, {"route_data": str(optimization_result)})
        
        # Return the optimization result in the legacy format
        return {
            "waypoint_order": optimization_result.get("waypoint_order", []),
            "schedule": optimization_result.get("schedule", []),
            "total_drive_time_minutes": optimization_result.get("total_drive_time_minutes", 0),
            "total_drive_distance_km": optimization_result.get("total_drive_distance_km", 0.0)
        }
    except Exception as e:
        logger.error(f"Error in legacy optimize endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    
    # Get port from environment variable or use default
    port = int(os.environ.get("PORT", 8000))
    
    # Run the application
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)
