# REanna Router CRM Monitoring Dashboard

## Overview

The CRM Monitoring Dashboard provides a comprehensive visual interface for monitoring the health and performance of the REanna Router CRM integration system. It allows operators to track API usage, monitor circuit breaker states, view rate limit consumption, and manage failed operations.

## Features

- **System Health Overview**: Real-time system health status with key metrics
- **API Statistics**: Detailed API call statistics with sorting, filtering and visualizations
- **Circuit Breaker Monitoring**: Visual display of circuit breaker states and transitions
- **Rate Limit Tracking**: Monitoring of API rate limit consumption with alerts
- **Failed Operations Management**: View and retry failed CRM sync operations

## Running the Dashboard

### Option 1: Using the Test Script

The easiest way to run the dashboard with test data is using the provided test script:

```bash
python scripts/test_dashboard.py
```

This script will:
1. Start the FastAPI server if not already running
2. Generate sample monitoring data
3. Create test failed operations
4. Open the dashboard in your default browser
5. Keep the server running until you press Ctrl+C

### Option 2: Manual Setup

If you want to run the dashboard with real production data:

1. Start the FastAPI server:
   ```bash
   uvicorn app.main:app --reload
   ```

2. Access the dashboard at:
   ```
   http://localhost:8000/dashboard
   ```

## Dashboard Sections

### 1. System Overview

The overview section provides a quick glance at the system health with:
- Overall system health status indicator
- Total API calls count
- Error rate percentage
- Circuit breaker states summary
- Rate limit status

### 2. API Statistics

Detailed API usage statistics for each endpoint:
- Success/failure counts
- Average response times
- 95th percentile response times
- Retry counts
- Visual charts showing relative usage and performance

### 3. Circuit Breakers

Visual indicators for each circuit breaker showing:
- Current state (CLOSED, OPEN, HALF-OPEN)
- Failure counts
- State change history
- Time spent in OPEN state

### 4. Rate Limits

For each rate-limited API endpoint:
- Percentage of rate limit consumed
- Remaining requests
- Reset time countdown
- Usage history graph

### 5. Failed Operations

Management console for CRM sync operations that failed:
- Filtering by operation type
- Error details and retry counts
- Retry buttons for individual operations
- Bulk retry option for all failed operations

## Integration Testing

The dashboard supports several integration testing scenarios:

1. To test successful synchronization:
   ```bash
   python scripts/test_rollout_integration.py
   ```

2. To test circuit breaker functionality:
   ```bash
   python scripts/test_circuit_breaker.py
   ```

3. To test the monitoring system:
   ```bash
   python scripts/test_monitoring.py
   ```

## Development Notes

- The dashboard updates automatically every 30 seconds
- Failed operations are stored in memory (not persistent across server restarts)
- The dashboard is responsive and works on mobile devices
- Charts use Chart.js for visualization

## Recommended Next Steps

- Implement persistent storage for failed operations
- Add email/Slack notifications for critical events
- Implement user authentication for the dashboard
- Add historical data tracking for trend analysis

## Troubleshooting

If you encounter issues:

1. Check the server logs for errors
2. Ensure all dependencies are installed
3. Verify the Rollout API credentials are correctly configured
4. Make sure the FastAPI server is running
5. Check if the static files are being served correctly