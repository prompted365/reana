"""
Test script for the monitoring dashboard.

This script:
1. Makes test API calls to generate monitoring data
2. Adds test failed operations
3. Opens the dashboard in a browser
"""

import sys
import os
import time
import signal
import random
import requests
import subprocess
from datetime import datetime, timedelta
import webbrowser
from urllib.parse import urljoin
import atexit

# Add parent directory to path so we can import app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils.monitoring import api_monitor, ApiMetricsContext
from app.utils.circuit_breaker import CircuitBreaker, CircuitState

# Configuration
BASE_URL = "http://localhost:8000"
SERVER_STARTED_CHECK_INTERVAL = 1.0  # seconds
MAX_SERVER_START_ATTEMPTS = 10

# Global server process reference
server_process = None

def start_server():
    """Start the FastAPI server using uvicorn."""
    global server_process
    
    print("Starting FastAPI server...")
    
    # Command to start the server
    cmd = ["uvicorn", "app.main:app", "--reload", "--host", "0.0.0.0", "--port", "8000"]
    
    try:
        # Start the server as a subprocess
        server_process = subprocess.Popen(
            cmd,
            stdout=None,  # Display stdout in console
            stderr=None,  # Display stderr in console
            text=True,
            bufsize=1
        )
        
        # Register cleanup function to ensure server is terminated
        atexit.register(stop_server)
        
        print(f"Server process started with PID: {server_process.pid}")
        return True
    except Exception as e:
        print(f"Error starting server: {str(e)}")
        return False

def stop_server():
    """Stop the FastAPI server."""
    global server_process
    
    if server_process:
        print(f"Stopping server process (PID: {server_process.pid})...")
        server_process.terminate()
        server_process = None
        print("Server stopped.")

def wait_for_server():
    """Wait for the server to start."""
    print("Waiting for server to start...")
    
    for attempt in range(MAX_SERVER_START_ATTEMPTS):
        try:
            response = requests.get(urljoin(BASE_URL, "/health"))
            if response.status_code == 200:
                print("Server is running!")
                return True
        except requests.RequestException:
            pass
        
        print(f"Waiting for server... (attempt {attempt + 1}/{MAX_SERVER_START_ATTEMPTS})")
        time.sleep(SERVER_STARTED_CHECK_INTERVAL)
    
    print("Server did not start in the expected time.")
    return False

def generate_test_data():
    """Generate test data for monitoring."""
    print("Generating test monitoring data...")
    
    # Generate API call statistics
    endpoints = [
        "/api/tours/optimize",
        "/api/tours/schedule",
        "/api/tours/cancel",
        "/api/feedback/submit",
        "/api/crm/sync-tours",
        "/api/crm/sync-feedback"
    ]
    
    # Record API calls with various success rates and response times
    for _ in range(50):
        endpoint = random.choice(endpoints)
        
        # Determine if this call will be successful (80% success rate)
        success = random.random() < 0.8
        
        # Generate random response time (50-500ms)
        response_time = random.uniform(0.05, 0.5)
        
        # Record more errors for CRM sync endpoints
        if "crm/sync" in endpoint:
            success = random.random() < 0.6
        
        # Use higher response times for optimization
        if "optimize" in endpoint:
            response_time = random.uniform(0.2, 1.0)
        
        # Record API call
        with ApiMetricsContext(endpoint) as ctx:
            ctx.set_success(success)
            if not success:
                ctx.set_retries(random.randint(0, 3))
        
        # Record rate limits for some endpoints
        if random.random() < 0.5:
            limit = 100
            remaining = random.randint(5, 95)
            reset_time = datetime.now() + timedelta(minutes=random.randint(10, 60))
            
            api_monitor.record_rate_limit(
                endpoint,
                limit,
                remaining,
                reset_time
            )
    
    # Generate circuit breaker states
    circuit_names = [
        "rollout_api",
        "rollout_mcp",
        "ghl_api",
        "lofty_api"
    ]
    
    # Record various circuit states
    for name in circuit_names:
        state = random.choice([CircuitState.CLOSED, CircuitState.OPEN, CircuitState.HALF_OPEN])
        failure_count = random.randint(0, 10)
        
        # Make rollout_api circuit more likely to be OPEN
        if name == "rollout_api" and random.random() < 0.7:
            state = CircuitState.OPEN
            failure_count = random.randint(5, 10)
        
        # Record circuit state
        circuit_breaker = CircuitBreaker(
            name=name,
            failure_threshold=5,
            recovery_timeout=30,
            half_open_max_calls=3
        )
        
        circuit_breaker._state = state
        circuit_breaker._failure_count = failure_count
        circuit_breaker._update_monitoring()

def add_test_failed_operations():
    """Add test failed operations for demonstration."""
    print("Adding test failed operations...")
    
    try:
        response = requests.post(urljoin(BASE_URL, "/api/monitoring/add-test-failed-operations"))
        
        if response.status_code == 200:
            result = response.json()
            print(f"Added {result.get('count', 0)} test failed operations")
        else:
            print(f"Failed to add test operations: {response.status_code} - {response.text}")
    
    except Exception as e:
        print(f"Error adding test operations: {str(e)}")

def open_dashboard():
    """Open the dashboard in a browser."""
    dashboard_url = urljoin(BASE_URL, "/dashboard")
    print(f"Opening dashboard at: {dashboard_url}")
    
    try:
        webbrowser.open(dashboard_url)
    except Exception as e:
        print(f"Error opening browser: {str(e)}")
        print(f"Please manually open: {dashboard_url}")

if __name__ == "__main__":
    print("===== CRM Monitoring Dashboard Test =====")
    
    try:
        # Start the server
        if start_server() and wait_for_server():
            # Generate test data
            generate_test_data()
            
            # Add test failed operations
            add_test_failed_operations()
            
            # Open dashboard
            open_dashboard()
            
            # Keep server running until user presses Ctrl+C
            print("\nDashboard is now running. Press Ctrl+C to exit.")
            try:
                while True:
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\nTest terminated by user.")
        else:
            print("Unable to start or connect to the server.")
            print("Please check for any error messages above.")
    except KeyboardInterrupt:
        print("\nTest terminated by user.")
    finally:
        # Ensure the server is stopped
        stop_server()