# CRM Integration Strategy for REanna Router

## Overview

This document outlines the architecture and implementation strategy for integrating REanna Router with multiple CRM systems (GoHighLevel, Lofty, etc.) using Rollout as an integration platform.

## Architecture

We've implemented a Model Context Protocol (MCP) server that serves as an abstraction layer between REanna Router and various CRM systems. This approach offers scalability, maintainability, and flexibility.

```
┌───────────────────┐      ┌────────────────────┐      ┌────────────────────┐
│                   │      │                    │      │                    │
│   REanna Router   │◄────►│  Rollout MCP Server│◄────►│  Rollout Platform  │◄────┐
│                   │      │                    │      │                    │     │
└───────────────────┘      └────────────────────┘      └────────────────────┘     │
                                                                                  │
                                                                                  ▼
                                                               ┌─────────┬─────────┬─────────┐
                                                               │         │         │         │
                                                               │GoHighlevel│  Lofty  │ Other CRMs│
                                                               │         │         │         │
                                                               └─────────┴─────────┴─────────┘
```

### Key Components

1. **REanna Router**: The core application that manages property tours and feedback
2. **Rollout MCP Server**: Middleware that standardizes CRM interactions
3. **Rollout Platform**: Integration platform with connectors to various CRMs
4. **CRM Systems**: Target systems where tour and feedback data is synchronized

## MCP Server Tools

Our MCP server (ID: `e552bffb-b799-4965-9e60-a2bfa664af91`) provides these tools:

1. **configure_rollout**:
   - Establishes connection to Rollout platform
   - Requires: `projectEnvKey`, `authToken`, and optional `baseUrl`

2. **list_available_crms**:
   - Lists available CRM connectors from Rollout platform
   - No required parameters

3. **configure_crm_connection**:
   - Sets up connection to a specific CRM system
   - Requires: `crmType` (e.g., 'hubspot', 'salesforce') and `credentialKey`

4. **sync_tour_data**:
   - Syncs tour schedules and property visits to CRMs
   - Requires: `tourData` (with tour details and properties) and `crmType`

5. **sync_feedback_data**:
   - Syncs buyer feedback to CRM contact records
   - Requires: `feedbackData` (with property and feedback details) and `crmType`

6. **create_automation**:
   - Creates custom automations in Rollout platform
   - Requires: `name`, `trigger`, and `action` details

## Implementation Guide

### 1. Initial Setup

```python
# Example: Setting up the Rollout integration
async def configure_crm_integration():
    """Set up the Rollout MCP integration"""
    
    # Configure connection to Rollout
    await mcp_client.call_tool(
        server_id="e552bffb-b799-4965-9e60-a2bfa664af91",
        tool_name="configure_rollout",
        arguments={
            "projectEnvKey": settings.ROLLOUT_PROJECT_KEY,
            "authToken": settings.ROLLOUT_AUTH_TOKEN
        }
    )
    
    # Configure GoHighLevel
    await mcp_client.call_tool(
        server_id="e552bffb-b799-4965-9e60-a2bfa664af91",
        tool_name="configure_crm_connection",
        arguments={
            "crmType": "gohighlevel",
            "credentialKey": settings.GOHIGHLEVEL_CREDENTIAL_KEY
        }
    )
    
    # Configure Lofty
    await mcp_client.call_tool(
        server_id="e552bffb-b799-4965-9e60-a2bfa664af91",
        tool_name="configure_crm_connection",
        arguments={
            "crmType": "lofty",
            "credentialKey": settings.LOFTY_CREDENTIAL_KEY
        }
    )
```

### 2. Syncing Tour Data

```python
# Example: Syncing a new tour to CRMs
async def sync_tour_to_crms(tour_id):
    """Sync a tour to connected CRM systems"""
    
    # Get tour details from database
    tour = await db.get_tour(tour_id)
    property_visits = await db.get_property_visits_for_tour(tour_id)
    
    # Format properties for sync
    properties = []
    for visit in property_visits:
        properties.append({
            "address": visit.address,
            "visitTime": visit.scheduled_arrival,
            "propertyId": visit.property_id
        })
    
    # Prepare tour data
    tour_data = {
        "tourData": {
            "tourId": tour.id,
            "agentId": tour.agent_id,
            "properties": properties
        },
        "crmType": "all"  # Sync to all configured CRMs
    }
    
    # Call MCP server to sync data
    result = await mcp_client.call_tool(
        server_id="e552bffb-b799-4965-9e60-a2bfa664af91",
        tool_name="sync_tour_data",
        arguments=tour_data
    )
    
    return result
```

### 3. Syncing Feedback Data

```python
# Example: Syncing property feedback to CRMs
async def sync_feedback_to_crms(feedback_id):
    """Sync feedback to connected CRM systems"""
    
    # Get feedback details from database
    feedback = await db.get_feedback(feedback_id)
    task = await db.get_task(feedback.task_id)
    property_visit = await db.get_property_visit(task.visit_id)
    
    # Prepare feedback data
    feedback_data = {
        "feedbackData": {
            "propertyId": property_visit.property_id,
            "tourId": property_visit.tour_id,
            "feedback": feedback.processed_feedback,
            "buyerId": property_visit.buyer_id,
            "timestamp": feedback.timestamp
        },
        "crmType": "all"  # Sync to all configured CRMs
    }
    
    # Call MCP server to sync data
    result = await mcp_client.call_tool(
        server_id="e552bffb-b799-4965-9e60-a2bfa664af91",
        tool_name="sync_feedback_data",
        arguments=feedback_data
    )
    
    return result
```

### 4. Creating Custom Automations

```python
# Example: Creating a custom automation for new feedback notifications
async def create_feedback_notification_automation():
    """Create an automation that notifies listing agents of new feedback"""
    
    automation_data = {
        "name": "New Feedback Notification",
        "trigger": {
            "appKey": "rollout-tools",
            "triggerKey": "webhook",
            "credentialKey": "webhook-cred-123",
            "inputParams": {
                "endpoint": "/feedback-webhook"
            }
        },
        "action": {
            "appKey": "gohighlevel",
            "actionKey": "create_task",
            "credentialKey": settings.GOHIGHLEVEL_CREDENTIAL_KEY,
            "inputParams": {
                "title": "Review New Property Feedback",
                "description": "{{data.feedback}}",
                "dueDate": "{{formatDate add='1' 'days' format='YYYY-MM-DD'}}",
                "assignedTo": "{{data.listingAgentId}}"
            }
        }
    }
    
    result = await mcp_client.call_tool(
        server_id="e552bffb-b799-4965-9e60-a2bfa664af91",
        tool_name="create_automation",
        arguments=automation_data
    )
    
    return result
```

## Data Mapping

### Tour Data Mapping

| REanna Router | CRM Concept |
|---------------|-------------|
| Tour | Calendar Event or Appointment Group |
| PropertyVisit | Individual Appointment or Task |
| Agent | User or Staff Member |
| Properties | Locations or Property Records |

### Feedback Data Mapping

| REanna Router | CRM Concept |
|---------------|-------------|
| Feedback | Note, Comment, or Activity |
| Property | Property Record or Deal |
| Buyer | Contact or Lead |
| Processed Feedback | Activity Description or Note Content |

## Benefits of This Approach

1. **Unified Interface**: One consistent API for all CRM operations
2. **Scalability**: Add new CRMs without changing REanna Router code
3. **Maintainability**: Isolate CRM-specific logic in the MCP server
4. **Flexibility**: Support different data mappings for each CRM
5. **Future-Proof**: Leverage new Rollout connectors as they become available

## Next Steps

1. **Enhance Error Handling**:
   - Implement retry logic for failed API calls
   - Add detailed logging for troubleshooting

2. **Add Credential Storage**:
   - Move from in-memory storage to secure persistent storage
   - Implement proper encryption for sensitive credentials

3. **Expand CRM Capabilities**:
   - Add bidirectional sync for selected data
   - Implement webhooks for real-time updates

4. **Monitoring and Alerts**:
   - Set up monitoring for API usage and rate limits
   - Create alerts for failed synchronizations

5. **Testing Framework**:
   - Develop comprehensive tests for each CRM integration
   - Create mock CRM responses for testing