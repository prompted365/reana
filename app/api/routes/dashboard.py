"""
Routes for serving the monitoring dashboard
"""

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import logging

# Configure logging
logger = logging.getLogger(__name__)

# Initialize templates
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Create router
router = APIRouter(
    tags=["dashboard"],
)

@router.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """
    Serve the monitoring dashboard.
    
    Args:
        request: The FastAPI request object
        
    Returns:
        HTML response with the dashboard
    """
    try:
        return templates.TemplateResponse(
            "dashboard.html", 
            {"request": request}
        )
    except Exception as e:
        logger.error(f"Error serving dashboard: {str(e)}")
        return HTMLResponse(
            content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>",
            status_code=500
        )