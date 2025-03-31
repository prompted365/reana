"""
Standalone test script for the monitoring dashboard.

This script creates a minimal FastAPI server that serves the dashboard
without depending on the full application infrastructure.
"""

import sys
import os
import time
import signal
import random
import subprocess
from datetime import datetime, timedelta
import webbrowser
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
import uvicorn
import json
import logging
import atexit
import threading

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Get the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"

# Create FastAPI app
app = FastAPI(
    title="REanna Router Monitoring Dashboard",
    description="A dashboard for monitoring CRM integration health",
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Setup templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Mock data for the monitoring endpoints
mock_api_stats = {
    "/api/tours/optimize": {
        "endpoint": "/api/tours/optimize",
        "success_count": 175,
        "error_count": 25,
        "retry_count": 15,
        "total_count": 200,
        "average_response_time": 0.85,
        "percentile_95": 1.2,
        "rate_limit_hits": 5,
        "last_called": (datetime.now() - timedelta(minutes=15)).isoformat()
    },
    "/api/tours/schedule": {
        "endpoint": "/api/tours/schedule",
        "success_count": 230,
        "error_count": 10,
        "retry_count": 5,
        "total_count": 240,
        "average_response_time": 0.45,
        "percentile_95": 0.8,
        "rate_limit_hits": 2,
        "last_called": (datetime.now() - timedelta(minutes=5)).isoformat()
    },
    "/api/crm/sync-tours": {
        "endpoint": "/api/crm/sync-tours",
        "success_count": 145,
        "error_count": 35,
        "retry_count": 25,
        "total_count": 180,
        "average_response_time": 1.2,
        "percentile_95": 2.5,
        "rate_limit_hits": 15,
        "last_called": (datetime.now() - timedelta(minutes=2)).isoformat()
    },
    "/api/crm/sync-feedback": {
        "endpoint": "/api/crm/sync-feedback",
        "success_count": 95,
        "error_count": 15,
        "retry_count": 10,
        "total_count": 110,
        "average_response_time": 0.95,
        "percentile_95": 1.8,
        "rate_limit_hits": 8,
        "last_called": (datetime.now() - timedelta(minutes=8)).isoformat()
    }
}

mock_rate_limits = {
    "/api/tours/optimize": {
        "endpoint": "/api/tours/optimize",
        "limit": 100,
        "remaining": 75,
        "reset_time": (datetime.now() + timedelta(minutes=25)).isoformat(),
        "last_updated": datetime.now().isoformat(),
        "percent_used": 25
    },
    "/api/crm/sync-tours": {
        "endpoint": "/api/crm/sync-tours",
        "limit": 50,
        "remaining": 5,
        "reset_time": (datetime.now() + timedelta(minutes=15)).isoformat(),
        "last_updated": datetime.now().isoformat(),
        "percent_used": 90
    }
}

mock_circuit_states = {
    "rollout_api": {
        "name": "rollout_api",
        "current_state": "OPEN",
        "failure_count": 8,
        "state_change_count": 3,
        "last_state_change": (datetime.now() - timedelta(minutes=10)).isoformat(),
        "last_failure": (datetime.now() - timedelta(minutes=10)).isoformat(),
        "last_success": (datetime.now() - timedelta(hours=1)).isoformat(),
        "open_duration": "0:10:00",
        "total_open_time": "1:30:00"
    },
    "rollout_mcp": {
        "name": "rollout_mcp",
        "current_state": "CLOSED",
        "failure_count": 2,
        "state_change_count": 1,
        "last_state_change": (datetime.now() - timedelta(hours=2)).isoformat(),
        "last_failure": (datetime.now() - timedelta(hours=2)).isoformat(),
        "last_success": (datetime.now() - timedelta(minutes=5)).isoformat(),
        "open_duration": "0:00:00",
        "total_open_time": "0:30:00"
    },
    "ghl_api": {
        "name": "ghl_api",
        "current_state": "HALF_OPEN",
        "failure_count": 5,
        "state_change_count": 2,
        "last_state_change": (datetime.now() - timedelta(minutes=30)).isoformat(),
        "last_failure": (datetime.now() - timedelta(minutes=35)).isoformat(),
        "last_success": (datetime.now() - timedelta(minutes=25)).isoformat(),
        "open_duration": "0:05:00",
        "total_open_time": "0:45:00"
    }
}

mock_failed_operations = [
    {
        "id": "f1234567",
        "operation": "Tour Sync - Property #12345",
        "type": "tour-sync",
        "status": "FAILED",
        "last_attempt": (datetime.now() - timedelta(minutes=30)).isoformat(),
        "retry_count": 3,
        "error": "API Connection Timeout"
    },
    {
        "id": "f7891011",
        "operation": "Feedback Sync - Client #54321",
        "type": "feedback-sync",
        "status": "PENDING_RETRY",
        "last_attempt": (datetime.now() - timedelta(hours=1)).isoformat(),
        "retry_count": 2,
        "error": "Rate Limit Exceeded"
    },
    {
        "id": "f1213141",
        "operation": "Tour Sync - Property #67890",
        "type": "tour-sync",
        "status": "FAILED",
        "last_attempt": (datetime.now() - timedelta(hours=2)).isoformat(),
        "retry_count": 5,
        "error": "Invalid Response Format"
    }
]

# API endpoints
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    """Serve the monitoring dashboard."""
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request}
    )

@app.get("/api/monitoring/api-stats")
async def get_api_stats():
    """Get API usage statistics."""
    return {
        "status": "success",
        "data": mock_api_stats
    }

@app.get("/api/monitoring/rate-limits")
async def get_rate_limits():
    """Get rate limit information."""
    return {
        "status": "success",
        "data": mock_rate_limits
    }

@app.get("/api/monitoring/circuit-states")
async def get_circuit_states():
    """Get circuit breaker states."""
    return {
        "status": "success",
        "data": mock_circuit_states
    }

@app.get("/api/monitoring/failed-operations")
async def get_failed_operations():
    """Get failed operations."""
    return {
        "status": "success",
        "data": mock_failed_operations
    }

@app.get("/api/monitoring/summary")
async def get_monitoring_summary():
    """Get a summary of all monitoring statistics."""
    # Calculate summary statistics
    total_api_calls = sum(stat["total_count"] for stat in mock_api_stats.values())
    total_errors = sum(stat["error_count"] for stat in mock_api_stats.values())
    total_retries = sum(stat["retry_count"] for stat in mock_api_stats.values())
    error_rate = (total_errors / total_api_calls) * 100 if total_api_calls > 0 else 0
    
    # Calculate average response time across all endpoints
    total_response_time = sum(stat["average_response_time"] * stat["success_count"] for stat in mock_api_stats.values())
    total_success_calls = sum(stat["success_count"] for stat in mock_api_stats.values())
    avg_response_time = total_response_time / total_success_calls if total_success_calls > 0 else 0
    
    # Get circuit breaker status
    open_circuits = [c for c in mock_circuit_states.values() if c["current_state"] == "OPEN"]
    half_open_circuits = [c for c in mock_circuit_states.values() if c["current_state"] == "HALF_OPEN"]
    
    # Get rate limit status
    rate_limit_status = "HEALTHY"
    lowest_remaining_percent = 100
    for limit in mock_rate_limits.values():
        if limit["limit"] > 0:
            remaining_percent = (limit["remaining"] / limit["limit"]) * 100
            if remaining_percent < lowest_remaining_percent:
                lowest_remaining_percent = remaining_percent
                
            if remaining_percent < 10:
                rate_limit_status = "WARNING"
            if remaining_percent < 5:
                rate_limit_status = "CRITICAL"
    
    # Determine overall system health
    system_health = "HEALTHY"
    if open_circuits or rate_limit_status == "CRITICAL":
        system_health = "DEGRADED"
    elif half_open_circuits or rate_limit_status == "WARNING" or error_rate > 10:
        system_health = "WARNING"
    
    return {
        "status": "success",
        "data": {
            "system_health": system_health,
            "api_stats": {
                "total_calls": total_api_calls,
                "total_errors": total_errors,
                "total_retries": total_retries,
                "error_rate": error_rate,
                "average_response_time": avg_response_time
            },
            "circuit_breakers": {
                "total": len(mock_circuit_states),
                "open": len(open_circuits),
                "half_open": len(half_open_circuits),
                "closed": len(mock_circuit_states) - len(open_circuits) - len(half_open_circuits)
            },
            "rate_limits": {
                "status": rate_limit_status,
                "lowest_remaining_percent": lowest_remaining_percent
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    }

@app.post("/api/monitoring/retry-operation/{operation_id}")
async def retry_operation(operation_id: str):
    """Retry a failed operation."""
    for op in mock_failed_operations:
        if op["id"] == operation_id:
            op["status"] = "PENDING_RETRY"
            op["retry_count"] += 1
            op["last_attempt"] = datetime.now().isoformat()
            return {
                "status": "success",
                "message": f"Operation {operation_id} queued for retry"
            }
    
    return {
        "status": "error",
        "message": f"Operation {operation_id} not found"
    }

@app.delete("/api/monitoring/delete-operation/{operation_id}")
async def delete_operation(operation_id: str):
    """Delete a failed operation."""
    global mock_failed_operations
    
    for i, op in enumerate(mock_failed_operations):
        if op["id"] == operation_id:
            mock_failed_operations.pop(i)
            return {
                "status": "success",
                "message": f"Operation {operation_id} deleted successfully"
            }
    
    return {
        "status": "error",
        "message": f"Operation {operation_id} not found"
    }

@app.post("/api/monitoring/retry-all-operations")
async def retry_all_operations():
    """Retry all failed operations."""
    retry_count = 0
    
    for op in mock_failed_operations:
        if op["status"] == "FAILED":
            op["status"] = "PENDING_RETRY"
            op["retry_count"] += 1
            op["last_attempt"] = datetime.now().isoformat()
            retry_count += 1
    
    return {
        "status": "success",
        "count": retry_count,
        "message": f"{retry_count} operations queued for retry"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

# Server functions
def start_server(host="0.0.0.0", port=8000):
    """Start the FastAPI server in a separate thread."""
    thread = threading.Thread(
        target=uvicorn.run,
        args=(app,),
        kwargs={
            "host": host,
            "port": port,
            "log_level": "info"
        },
        daemon=True
    )
    thread.start()
    return thread

def wait_for_server(url="http://localhost:8000/health", timeout=10):
    """Wait for the server to start."""
    import requests
    from urllib.error import URLError
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = requests.get(url)
            if response.status_code == 200:
                return True
        except (requests.RequestException, URLError):
            pass
        
        time.sleep(0.5)
    
    return False

def open_dashboard(url="http://localhost:8000/dashboard"):
    """Open the dashboard in a web browser."""
    webbrowser.open(url)

if __name__ == "__main__":
    try:
        print("===== Starting Standalone Dashboard =====")
        
        # Start the server
        print("Starting the server...")
        server_thread = start_server()
        
        # Wait for the server to start
        if wait_for_server():
            print("Server is running!")
            
            # Open the dashboard
            print("Opening dashboard...")
            open_dashboard()
            
            print("\nDashboard is now running at http://localhost:8000/dashboard")
            print("Press Ctrl+C to exit.")
            
            # Keep the script running until interrupted
            while True:
                time.sleep(1)
        else:
            print("Server did not start correctly.")
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    except Exception as e:
        print(f"Error: {str(e)}")