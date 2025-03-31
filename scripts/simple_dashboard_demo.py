"""
Simple dashboard demo without external dependencies.

This script serves a minimal dashboard demo using FastAPI's built-in
response types without requiring Jinja2 templates.
"""

import time
import webbrowser
import threading
from datetime import datetime, timedelta
from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

# Create FastAPI app
app = FastAPI(
    title="REanna Router Monitoring Dashboard",
    description="A dashboard for monitoring CRM integration health",
)

# Get the project root directory
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "app" / "static"

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

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
    }
]

# Simple HTML for dashboard
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REanna Router - CRM Monitoring Dashboard</title>
    <link rel="stylesheet" href="/static/css/styles.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js@3.7.0/dist/chart.min.js"></script>
</head>
<body>
    <header>
        <div class="header-container">
            <h1>REanna Router - CRM Integration Dashboard</h1>
            <div class="system-status">
                <span id="system-health-label">System Health:</span>
                <span id="system-health" class="health-status health-unknown">Unknown</span>
                <span id="last-updated"></span>
            </div>
        </div>
    </header>
    <nav>
        <ul>
            <li><a href="#overview" class="active" data-target="overview-section">Overview</a></li>
            <li><a href="#api-stats" data-target="api-stats-section">API Statistics</a></li>
            <li><a href="#circuit-breakers" data-target="circuit-breakers-section">Circuit Breakers</a></li>
            <li><a href="#failed-operations" data-target="failed-operations-section">Failed Operations</a></li>
        </ul>
    </nav>
    <main>
        <div id="overview-section" class="dashboard-section active">
            <h2>System Overview</h2>
            <div class="overview-grid">
                <div class="card">
                    <div class="card-header">
                        <h3>API Calls</h3>
                    </div>
                    <div class="card-body">
                        <div class="metric-large">
                            <span id="total-api-calls">-</span>
                        </div>
                        <div class="metric-subtitle">Total Requests</div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <h3>Error Rate</h3>
                    </div>
                    <div class="card-body">
                        <div class="metric-large" id="error-rate-container">
                            <span id="error-rate">-</span><span>%</span>
                        </div>
                        <div class="metric-subtitle">
                            <span id="total-errors">-</span> errors / <span id="total-retries">-</span> retries
                        </div>
                    </div>
                </div>
                <div class="card">
                    <div class="card-header">
                        <h3>Circuit Breakers</h3>
                    </div>
                    <div class="card-body">
                        <div class="circuit-status">
                            <span class="status-label">Open:</span>
                            <span id="open-circuits" class="status-count">-</span>
                        </div>
                        <div class="circuit-status">
                            <span class="status-label">Half-Open:</span>
                            <span id="half-open-circuits" class="status-count">-</span>
                        </div>
                        <div class="circuit-status">
                            <span class="status-label">Closed:</span>
                            <span id="closed-circuits" class="status-count">-</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="chart-container">
                <div class="chart-card">
                    <h3>API Calls by Endpoint</h3>
                    <canvas id="api-calls-chart"></canvas>
                </div>
            </div>
        </div>
    </main>
    <footer>
        <p>&copy; 2025 REanna Router - CRM Monitoring Dashboard</p>
    </footer>

    <script>
        // Fetch data and update dashboard
        async function fetchData() {
            try {
                // Fetch summary data
                const summaryResponse = await fetch('/api/monitoring/summary');
                const summaryData = await summaryResponse.json();
                
                if (summaryData.status === 'success') {
                    updateSummary(summaryData.data);
                }
                
                // Fetch API stats
                const apiStatsResponse = await fetch('/api/monitoring/api-stats');
                const apiStatsData = await apiStatsResponse.json();
                
                if (apiStatsData.status === 'success') {
                    updateApiChart(apiStatsData.data);
                }
                
                // Set refresh timer
                setTimeout(fetchData, 30000);
            } catch (error) {
                console.error('Error fetching data:', error);
            }
        }
        
        // Update system summary
        function updateSummary(data) {
            // Update system health
            const healthElement = document.getElementById('system-health');
            healthElement.textContent = data.system_health;
            healthElement.className = 'health-status';
            healthElement.classList.add('health-' + data.system_health.toLowerCase());
            
            // Update last updated time
            const date = new Date(data.timestamp);
            document.getElementById('last-updated').textContent = 
                `Last updated: ${date.toLocaleTimeString()}`;
            
            // Update metrics
            document.getElementById('total-api-calls').textContent = 
                data.api_stats.total_calls.toLocaleString();
            document.getElementById('total-errors').textContent = 
                data.api_stats.total_errors.toLocaleString();
            document.getElementById('total-retries').textContent = 
                data.api_stats.total_retries.toLocaleString();
            document.getElementById('error-rate').textContent = 
                data.api_stats.error_rate.toFixed(2);
            
            // Update circuit breaker counts
            document.getElementById('open-circuits').textContent = data.circuit_breakers.open;
            document.getElementById('half-open-circuits').textContent = data.circuit_breakers.half_open;
            document.getElementById('closed-circuits').textContent = data.circuit_breakers.closed;
        }
        
        // Update API chart
        function updateApiChart(data) {
            const ctx = document.getElementById('api-calls-chart');
            
            // Extract data for chart
            const endpoints = Object.values(data).sort((a, b) => b.total_count - a.total_count);
            
            const labels = endpoints.map(endpoint => {
                return endpoint.endpoint.length > 25
                    ? endpoint.endpoint.substring(0, 22) + '...'
                    : endpoint.endpoint;
            });
            
            const successData = endpoints.map(endpoint => endpoint.success_count);
            const errorData = endpoints.map(endpoint => endpoint.error_count);
            
            // Create chart
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: labels,
                    datasets: [
                        {
                            label: 'Successful Calls',
                            data: successData,
                            backgroundColor: 'rgba(46, 204, 113, 0.5)',
                            borderColor: 'rgba(46, 204, 113, 1)',
                            borderWidth: 1
                        },
                        {
                            label: 'Failed Calls',
                            data: errorData,
                            backgroundColor: 'rgba(231, 76, 60, 0.5)',
                            borderColor: 'rgba(231, 76, 60, 1)',
                            borderWidth: 1
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: true,
                            title: {
                                display: true,
                                text: 'Number of API Calls'
                            },
                            stacked: true
                        },
                        x: {
                            stacked: true
                        }
                    },
                    plugins: {
                        legend: {
                            position: 'top',
                        }
                    }
                }
            });
        }
        
        // Initialize
        document.addEventListener('DOMContentLoaded', () => {
            fetchData();
        });
    </script>
</body>
</html>
"""

# API endpoints
@app.get("/dashboard", response_class=HTMLResponse)
async def get_dashboard():
    """Serve the monitoring dashboard."""
    return HTMLResponse(content=DASHBOARD_HTML)

@app.get("/api/monitoring/api-stats")
async def get_api_stats():
    """Get API usage statistics."""
    return JSONResponse({
        "status": "success",
        "data": mock_api_stats
    })

@app.get("/api/monitoring/circuit-states")
async def get_circuit_states():
    """Get circuit breaker states."""
    return JSONResponse({
        "status": "success",
        "data": mock_circuit_states
    })

@app.get("/api/monitoring/failed-operations")
async def get_failed_operations():
    """Get failed operations."""
    return JSONResponse({
        "status": "success",
        "data": mock_failed_operations
    })

@app.get("/api/monitoring/summary")
async def get_monitoring_summary():
    """Get a summary of all monitoring statistics."""
    # Calculate summary statistics
    total_api_calls = sum(stat["total_count"] for stat in mock_api_stats.values())
    total_errors = sum(stat["error_count"] for stat in mock_api_stats.values())
    total_retries = sum(stat["retry_count"] for stat in mock_api_stats.values())
    error_rate = (total_errors / total_api_calls) * 100 if total_api_calls > 0 else 0
    
    # Get circuit breaker status
    open_circuits = [c for c in mock_circuit_states.values() if c["current_state"] == "OPEN"]
    half_open_circuits = [c for c in mock_circuit_states.values() if c["current_state"] == "HALF_OPEN"]
    
    # Determine overall system health
    system_health = "HEALTHY"
    if open_circuits:
        system_health = "DEGRADED"
    elif half_open_circuits or error_rate > 10:
        system_health = "WARNING"
    
    return JSONResponse({
        "status": "success",
        "data": {
            "system_health": system_health,
            "api_stats": {
                "total_calls": total_api_calls,
                "total_errors": total_errors,
                "total_retries": total_retries,
                "error_rate": error_rate,
                "average_response_time": 0.8
            },
            "circuit_breakers": {
                "total": len(mock_circuit_states),
                "open": len(open_circuits),
                "half_open": len(half_open_circuits),
                "closed": len(mock_circuit_states) - len(open_circuits) - len(half_open_circuits)
            },
            "timestamp": datetime.utcnow().isoformat()
        }
    })

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return JSONResponse({"status": "healthy"})

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
        print("===== Starting Simple Dashboard Demo =====")
        
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
