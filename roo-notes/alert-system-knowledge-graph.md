# REanna Router Alert System Knowledge Graph

This document visualizes the structure and relationships of the alert system components using a knowledge graph approach. The graph represents files, classes, processes, and their interconnections.

## Core Components

### Modules

- **alert_manager.py**: Core module defining the alert management system
- **monitoring.py**: API routes for monitoring system health
- **circuit_breaker.py**: Implements the circuit breaker pattern for API resilience
- **notification_service.py**: Service for sending notifications and syncing with CRMs
- **rollout_client.py**: Client library for Rollout API integration
- **dashboard.html/js**: Frontend components for displaying alerts and monitoring data
- **test_alerts.py**: Test script demonstrating the alert system functionality

### Classes

- **AlertLevel** (Enum): INFO, WARNING, ERROR, CRITICAL
- **AlertType** (Enum): REPEATED_SYNC_FAILURE, CIRCUIT_BREAKER_OPEN, RATE_LIMIT_CRITICAL, etc.
- **AlertMethod** (Enum): LOG, EMAIL, WEBHOOK, SLACK
- **AlertConfig**: Configuration class for alerts (thresholds, windows, methods)
- **AlertEvent**: Data model for triggered alerts
- **AlertManager**: Central manager class for the alert system
- **FailedOperation**: Data model for tracking failed operations
- **CircuitBreaker**: Implements the circuit breaker pattern

## Architecture Diagram

```
┌───────────────────┐                ┌────────────────────┐
│  alert_manager.py │◄───imports─────┤    monitoring.py   │
│                   │                │                    │
│  - AlertLevel     │◄───imports─────┤  - FailedOperation │
│  - AlertType      │                └────────────────────┘
│  - AlertMethod    │                         ▲
│  - AlertConfig    │                         │
│  - AlertEvent     │                         │imports
│  - AlertManager   │◄────notifies────┐       │
└───────────────────┘                 │       │
          ▲                           │       │
          │                           │       │
          │uses                       │       │
          │                           │       │
┌─────────┴─────────┐         ┌──────┴───────┴───┐
│ notification_     │         │  circuit_breaker  │
│ service.py        │◄────────┤                   │
│                   │  uses   │  - CircuitBreaker │
└───────────────────┘         └───────────────────┘
          │                             
          │uses                          
          ▼                             
┌───────────────────┐                   
│  rollout_client.py│                   
│                   │                   
└───────────────────┘                   
```

## Module Dependency Graph

```
main.py
  │
  ├──imports──> api/routes/__init__.py
  │               │
  │               └──imports──> monitoring.py
  │                               │
  │                               ├──imports──> alert_manager.py
  │                               │
  │                               └──imports──> circuit_breaker.py
  │
  └──initialized_by──> alert_manager.py
                        │
                        └──exports──> utils/__init__.py
```

## Import/Export Structure

```
┌─────────────────────────────────────────────────────────┐
│                  imports_structure                       │
│                                                         │
│  ┌─────────────────┐    ┌─────────────┐    ┌──────────┐ │
│  │ services/       │    │ utils/      │    │ api/     │ │
│  │ __init__.py     │    │ __init__.py │    │ routes/  │ │
│  │                 │    │             │    │ __init__ │ │
│  │ - exports from  │    │ - exports   │    │          │ │
│  │   service modules│    │   utility   │    │ - registers│ │
│  └─────────────────┘    │   modules   │    │   routers │ │
│                         └─────────────┘    └──────────┘ │
└─────────────────────────────────────────────────────────┘
```

## Error Handling Flow

```
┌─────────────────┐     ┌────────────────┐     ┌───────────────┐
│ notification_   │     │ alert_manager  │     │ dashboard.js  │
│ service.py      │────>│                │────>│               │
│                 │     │ record_        │     │ fetches and   │
│ Operation fails │     │ operation_     │     │ displays      │
│ and is recorded │     │ failure        │     │ alerts        │
└─────────────────┘     └────────────────┘     └───────────────┘
                              │
                              │ creates
                              ▼
                        ┌────────────────┐
                        │ AlertEvent     │
                        │ (if threshold  │
                        │  exceeded)     │
                        └────────────────┘
                              │
                              │ delivered via
                              ▼
                        ┌────────────────┐
                        │ LOG, EMAIL,    │
                        │ WEBHOOK, SLACK │
                        └────────────────┘
```

## Test Script Workflow

The `test_alerts.py` script demonstrates the alert system by:

1. Configuring alert thresholds for testing
2. Generating test failures to trigger alerts 
3. Simulating a circuit breaker open event
4. Showing how to view results in the dashboard

```
test_alerts.py
    │
    ├───imports───> alert_manager.py
    │                 │
    │                 ├── AlertType
    │                 ├── AlertLevel  
    │                 ├── AlertMethod
    │                 ├── AlertConfig
    │                 └── AlertManager
    │
    └───imports───> monitoring.py
                     │
                     └── FailedOperation
```

This knowledge graph provides a comprehensive view of the alert system's architecture, showing how components interact and how data flows through the system during normal operation and error conditions.