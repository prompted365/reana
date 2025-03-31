# REanna Router Knowledge Graph Index

This document serves as an index to the comprehensive knowledge graphs that map the architecture of the REanna Router application.

## Knowledge Graph Documents

1. [**Application Architecture**](application-architecture-knowledge-graph.md) - High-level overview of the entire application structure
   - Main application components and their relationships
   - Entry point structure and router registration
   - Complete system data flow

2. [**Services Architecture**](services-architecture-knowledge-graph.md) - Detailed mapping of the service layer
   - Service layer overview 
   - Individual service details and relationships
   - Data flow through services
   - Service-router interactions

3. [**Error Handling System**](error-handling-knowledge-graph.md) - Comprehensive view of error handling
   - Error propagation flow
   - Circuit breaker pattern implementation
   - Error types and classification
   - Alert generation process

4. [**Alert System**](alert-system-knowledge-graph.md) - Focused view of the alert management system
   - Core alert components and relationships
   - Alert types, levels, and methods
   - Alert configuration options
   - Alert notification flow

## System Overview Diagram

The REanna Router architecture can be summarized in this high-level diagram:

```
┌─────────────────────────────────────────────────────────────┐
│                         main.py                             │
│                   (Application Entry Point)                 │
└───────────────────────────┬─────────────────────────────────┘
                            │
         ┌─────────────────┬┴───────────────┬─────────────────┐
         │                 │                │                 │
┌────────▼────────┐ ┌──────▼─────────┐ ┌────▼────────┐ ┌──────▼─────────┐
│   API Routes    │ │ Database Init  │ │Static Files │ │ Error Handling │
└────────┬────────┘ └──────┬─────────┘ └────┬────────┘ └──────┬─────────┘
         │                 │                │                 │
    ┌────┴────────────────┬┘                └────────┬───────┐
    │                     │                          │       │
┌───▼─────────┐   ┌───────▼───────┐           ┌──────▼───┐   │
│ Data Models │   │ Service Layer │           │Dashboard │   │
└─────────────┘   └───────┬───────┘           └──────────┘   │
                          │                                  │
          ┌───────────────┼────────────────┐                 │
          │               │                │                 │
┌─────────▼─────┐ ┌───────▼─────┐  ┌───────▼────────┐ ┌──────▼─────────┐
│Optimization   │ │Notification │  │Alert & Monitor │ │Circuit Breaker │
│Service        │ │Service      │  │Service         │ │Protection      │
└─────────┬─────┘ └─────┬───────┘  └───────┬────────┘ └────────────────┘
          │             │                  │
          └─────────────┼──────────────────┘
                        │
                ┌───────▼───────┐
                │RolloutClient  │
                │(External API) │
                └───────────────┘
```

## Key Component Relationships

The following relationships are crucial to understanding the system:

1. **Router → Service**: API routers use services to implement business logic
   - Example: `tours_router` uses `OptimizationService` for route planning

2. **Service → Model**: Services interact with data models for persistence
   - Example: `OptimizationService` creates and updates `Tour` and `PropertyVisit` models

3. **Service → Service**: Services collaborate to accomplish tasks
   - Example: `NotificationService` uses `RolloutClient` for external communication

4. **Service → Error Handling**: Services report errors to monitoring components
   - Example: `RolloutClient` errors are caught and forwarded to `CircuitBreaker` and `AlertManager`

## Data Flow Sequences

The application handles several key data flows:

1. **Tour Creation and Optimization**:
   - API Request → `tours_router` → `OptimizationService` → Database → External API

2. **Feedback Collection and Notification**:
   - API Request → `feedback_router` → `NotificationService` → `RolloutClient` → External API

3. **Error Handling and Alert Generation**:
   - Service Failure → `CircuitBreaker` → `AlertManager` → Notification Channels → Dashboard

4. **Monitoring and Visualization**:
   - System Events → Monitoring Data → API Endpoints → Dashboard UI

## Technology Stack

The application uses the following key technologies:

- **Web Framework**: FastAPI
- **Database**: SQLite
- **Template Engine**: Jinja2
- **External APIs**: Google Maps Route Optimization, Rollout CRM API
- **Frontend**: HTML, CSS, JavaScript

## Testing Structure

The application includes several test scripts that validate different components:

- `test_alerts.py`: Verifies alert triggering and notification
- `test_circuit_breaker.py`: Tests circuit breaker state transitions
- `test_monitoring.py`: Validates monitoring data collection
- `test_dashboard.py`: Ensures dashboard correctly displays system state

This index provides navigation to the detailed knowledge graphs while giving a high-level overview of the REanna Router application architecture.