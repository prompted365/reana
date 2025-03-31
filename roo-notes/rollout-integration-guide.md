# Rollout CRM Integration Guide

This guide explains how to use and test the Rollout CRM integration with REanna Router.

## Overview

The integration allows REanna Router to sync tour schedules and feedback to multiple CRM systems through the Rollout platform. We've implemented:

1. A secure configuration setup for Rollout credentials
2. A JWT token generator for Rollout API authentication
3. A Rollout API client for interacting with the platform
4. Integration with the notification service for feedback sync
5. Integration with the tours API for tour schedule sync
6. An MCP server (ID: `e552bffb-b799-4965-9e60-a2bfa664af91`) that provides a unified interface

## Testing the Integration

### Prerequisites

1. Make sure you have installed the required dependencies:

```bash
pip install python-dotenv pyjwt aiohttp
```

2. Verify that the Rollout credentials are correctly set in `config/rollout.env`

### Testing Tour Sync to CRM

1. Create a new tour with the CRM sync enabled:

```bash
curl -X POST "http://localhost:8000/tours/?sync_to_crm=true" \
  -H "Content-Type: application/json" \
  -d '{
    "agent_id": "agent-123",
    "property_addresses": [
      "123 Main St, New York, NY",
      "456 Park Ave, New York, NY",
      "789 Broadway, New York, NY"
    ],
    "start_time": "2025-04-01T09:00:00Z",
    "strategy": "OPTIMIZE"
  }'
```

2. Check the logs to confirm that the tour was synced to CRM systems

3. Alternatively, manually trigger a sync for an existing tour:

```bash
curl -X POST "http://localhost:8000/tours/YOUR_TOUR_ID/sync-to-crm"
```

### Testing Feedback Sync to CRM

1. Record a property visit arrival and departure:

```bash
# Record arrival
curl -X POST "http://localhost:8000/property-visits/YOUR_VISIT_ID/arrival" \
  -H "Content-Type: application/json" \
  -d '{
    "actual_arrival": "2025-04-01T10:00:00Z"
  }'

# Record departure
curl -X POST "http://localhost:8000/property-visits/YOUR_VISIT_ID/departure" \
  -H "Content-Type: application/json" \
  -d '{
    "actual_departure": "2025-04-01T10:30:00Z"
  }'
```

2. Submit feedback for the property:

```bash
curl -X POST "http://localhost:8000/feedback/" \
  -H "Content-Type: application/json" \
  -d '{
    "task_id": "YOUR_FEEDBACK_TASK_ID",
    "raw_feedback": "Loved the kitchen but the bathroom needs updating.",
    "feedback_source": "APP"
  }'
```

3. Check the logs to confirm that the feedback was synced to CRM systems

## How It Works

### CRM Data Flow

```
1. REanna Router creates a tour or receives feedback
2. REanna formats the data for CRM integration
3. REanna calls the Rollout MCP server tools
4. MCP server transforms data for specific CRMs
5. MCP server calls Rollout API to execute the integrations
6. Rollout syncs data to connected CRM systems
```

### Available CRM Integrations

The Rollout platform supports numerous CRM integrations, including:

- HubSpot
- Salesforce
- Zoho CRM
- Pipedrive
- Many others via the Rollout connector ecosystem

To add support for a new CRM:

1. Connect to the CRM in the Rollout platform
2. Get the credential key for the CRM
3. Configure the connection with the `configure_crm_connection` tool

## Troubleshooting

### Authentication Issues

If you encounter authentication errors:

1. Verify that the correct credentials are in `config/rollout.env`
2. Check that the JWT token is being generated correctly
3. Ensure that the token has not expired (tokens are valid for 1 hour)

### CRM Sync Issues

If sync operations fail:

1. Check the logs for specific error messages
2. Verify that the CRM is properly configured in Rollout
3. Ensure that the data format matches what the CRM expects

### MCP Server Issues

If the MCP server is not responding or returning errors:

1. Verify that the server ID is correct
2. Check that the server is running and accessible
3. Try restarting the MCP server if necessary

## Monitoring and Maintenance

1. **Monitor API usage**: The Rollout platform may have rate limits
2. **Refresh credentials**: If credentials expire, update them in `config/rollout.env`
3. **Check sync status**: Monitor logs for any failed sync operations
4. **Update mappings**: If CRM data models change, update the mappings in the MCP server

## Next Steps for Production

1. **Implement credential encryption**: Store sensitive credentials securely
2. **Add retry logic**: Implement retries for failed API calls
3. **Add monitoring**: Set up alerts for integration failures
4. **Implement rate limiting**: Handle API rate limits gracefully
5. **Add admin UI**: Create an interface for managing CRM connections
