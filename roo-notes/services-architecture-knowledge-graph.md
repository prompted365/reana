# REanna Router Services Architecture Knowledge Graph

This document maps the services layer of the REanna Router application, focusing on how the various services interact with each other, the data models, and the API endpoints.

## 1. Service Layer Overview

The REanna Router application is built around several core services that encapsulate business logic:

```
┌───────────────────────────────────────────────┐
│             Services Layer                    │
└──────────┬────────────────┬──────────┬────────┘
           │                │          │
┌──────────▼─────┐  ┌───────▼──────┐  ┌▼────────────────┐
│ Optimization   │  │ Notification │  │ Alert & Monitor │
│ Services       │  │ Services     │  │ Services        │
└──────────┬─────┘  └───────┬──────┘  └─┬──────────────┬┘
           │                │           │              │
┌──────────▼────────────────▼───┐    ┌──▼─────────┐  ┌─▼────────────┐
│ External API Integration      │    │ Alert      │  │ Circuit      │
│ Services                      │    │ Manager    │  │ Breaker      │
└─────────────────────────┬─────┘    └────────────┘  └──────────────┘
                          │
                ┌─────────▼────────┐
                │  RolloutClient   │
                └──────────────────┘
```

## 2. Optimization Service

The Optimization Service is responsible for planning and scheduling real estate tours:

```
┌───────────────────────────────────────────────────────────────────┐
│                     OptimizationService                           │
└────────────────────────────────┬──────────────────────────────────┘
                                 │
                    ┌────────────┴───────────────┐
                    │                            │
        ┌───────────▼────────────┐    ┌──────────▼─────────┐
        │ create_and_optimize_   │    │ Google Maps        │
        │ tour                   │    │ Route Optimization │
        └───────────┬────────────┘    │ API                │
                    │                 └──────────────┬─────┘
                    │                                │
        ┌───────────▼────────────┐    ┌──────────────▼─────┐
        │ Tour Creation          │    │ Route Calculation  │
        │ (Database)             │    │ and Optimization   │
        └───────────┬────────────┘    └───────────┬────────┘
                    │                             │
                    │                             │
        ┌───────────▼────────────┐    ┌───────────▼────────┐
        │ Property Visit         │    │ Time Window        │
        │ Creation               │    │ Assignment         │
        └───────────┬────────────┘    └───────────┬────────┘
                    │                             │
                    │                             │
                    └─────────────────────────────┘
                                 │
                    ┌────────────▼───────────────┐
                    │ Task Creation              │
                    │ (For each property visit)  │
                    └────────────────────────────┘
```

### Key Functions:

* **create_and_optimize_tour**: Main entry point for creating and optimizing a tour
* **optimize_tour**: Calls Google Maps API to find the best route
* **map_properties_to_shipments**: Translates property visits to the format needed by the API
* **parse_optimization_response**: Processes response and updates database

## 3. Notification Service

The Notification Service handles communication with agents and CRM systems:

```
┌────────────────────────────────────────────────────────────────┐
│                     NotificationService                        │
└────────────┬─────────────────────────────────┬─────────────────┘
             │                                 │
  ┌──────────▼────────────┐      ┌─────────────▼──────────┐
  │ notify_listing_agent  │      │ sync_tour_to_crm       │
  └──────────┬────────────┘      └─────────────┬──────────┘
             │                                 │
  ┌──────────▼────────────┐      ┌─────────────▼──────────┐
  │ _send_notification_   │      │ rollout_client         │
  │ to_agent              │      │ sync_tour              │
  └──────────┬────────────┘      └─────────────┬──────────┘
             │                                 │
             │                                 │
  ┌──────────▼────────────┐      ┌─────────────▼──────────┐
  │ Log, Email, SMS       │      │ Error Handling         │
  │ (simulated)           │      │ and Retry Logic        │
  └─────────────────┬─────┘      └─────────────┬──────────┘
                    │                          │
                    │                          │
  ┌─────────────────▼──────────────────────────▼──────────┐
  │                      Alert Manager                    │
  │             (For error tracking and alerts)           │
  └──────────────────────────────────────────────────────┬┘
                                                         │
                                         ┌───────────────▼──────────────┐
                                         │     Failed Operations        │
                                         │        Tracking              │
                                         └──────────────────────────────┘
```

### Key Methods:

* **notify_listing_agent**: Sends notifications to listing agents about feedback
* **sync_feedback_to_crm**: Sends feedback data to CRM systems
* **sync_tour_to_crm**: Syncs tour information with CRM systems
* **process_unsent_feedback**: Background job to process pending notifications

## 4. RolloutClient

The RolloutClient handles all external API communication with the Rollout system:

```
┌────────────────────────────────────────────────────────────────┐
│                       RolloutClient                            │
└──────┬───────────────────────────────────────┬─────────────────┘
       │                                       │
┌──────▼───────────────────┐    ┌──────────────▼─────────────────┐
│ Authentication           │    │ API Calls                      │
│ (JWT Generation)         │    │ (Sync operations)              │
└──────┬───────────────────┘    └──────────────┬─────────────────┘
       │                                       │
       │                                       │
┌──────▼───────────────────┐    ┌──────────────▼─────────────────┐
│ rollout_auth.py          │    │ sync_tour, sync_feedback       │
└────────────────────┬─────┘    └───────────────┬────────────────┘
                     │                          │
                     │                          │
                     └──────────────┬───────────┘
                                    │
                          ┌─────────▼────────────┐
                          │ Circuit Breaker      │
                          │ Protection           │
                          └─────────┬────────────┘
                                    │
                          ┌─────────▼────────────┐
                          │ Error Types:         │
                          │ - RolloutRateLimitErr│
                          │ - RolloutServerError │
                          │ - RolloutCircuitOpen │
                          └─────────────┬────────┘
                                        │
                                        │
                               ┌────────▼────────┐
                               │ Error Propagation│
                               │ to Services     │
                               └─────────────────┘
```

### Key Features:

* **Authentication**: JWT token generation and management
* **Circuit Breaker Integration**: Protected API calls
* **Error Classification**: Specific error types for different failure modes
* **Retry Handling**: Implemented at the service layer using these error types

## 5. Alert and Monitoring Services

The alert and monitoring services provide visibility into system health:

```
┌──────────────────────────────────────────────────────────────────┐
│                      AlertManager                                │
└──────────────────────────────────┬───────────────────────────────┘
                                   │
                    ┌──────────────┴────────────────┐
                    │                               │
       ┌────────────▼─────────────┐     ┌───────────▼────────────┐
       │ Threshold-based           │     │ Notification Delivery  │
       │ Alert Triggering         │     │ Channels               │
       └────────────┬─────────────┘     └──────────┬─────────────┘
                    │                              │
       ┌────────────▼─────────────┐     ┌──────────▼─────────────┐
       │ record_operation_failure │     │ _send_log_alert        │
       └────────────┬─────────────┘     │ _send_email_alert      │
                    │                   │ _send_webhook_alert    │
                    │                   │ _send_slack_alert      │
                    │                   └──────────────────┬─────┘
                    │                                      │
                    └──────────────────────────────────────┘
                                    │
                       ┌────────────▼───────────────┐
                       │ Dashboard Integration      │
                       │ (API endpoints)            │
                       └────────────────────────────┘
```

### Key Components:

* **AlertManager**: Central service for tracking failures and sending alerts
* **CircuitBreaker**: Prevents cascading failures from external API issues
* **Monitoring API**: Provides system health data to the dashboard

## 6. Service Interactions With Routers

The services are connected to the API endpoints through the routers:

```
┌────────────────────────────────────────────────────────────────┐
│                      API Routers                               │
└─────────┬──────────────┬────────────────┬──────────────────────┘
          │              │                │
┌─────────▼─────┐ ┌──────▼───────┐ ┌──────▼────────┐ ┌───────────┐
│ tours_router  │ │feedback_router│ │monitoring_    │ │dashboard_ │
└─────────┬─────┘ └──────┬───────┘ │router         │ │router     │
          │              │         └──────┬────────┘ └───────────┘
          │              │                │
┌─────────▼─────┐ ┌──────▼───────┐ ┌──────▼────────┐
│Optimization   │ │Notification  │ │Alert & Monitor│
│Service        │ │Service       │ │Services       │
└─────────┬─────┘ └──────┬───────┘ └──────┬────────┘
          │              │                │
          └──────────────┼────────────────┘
                         │
                ┌────────▼──────────┐
                │   RolloutClient   │
                └───────────────────┘
```

### Router to Service Mapping:

* **tours_router**: Uses OptimizationService and NotificationService
* **feedback_router**: Uses NotificationService
* **monitoring_router**: Uses AlertManager and CircuitBreaker data
* **dashboard_router**: Provides UI for monitoring data

## 7. Data Flow Through Services

The complete data flow through the services follows this pattern:

```
           ┌────────────────┐
API Request│ Tours Router   │
───────────► create_tour    │
           └──────┬─────────┘
                  │
                  ▼
        ┌──────────────────┐
        │ OptimizationSvc  │
        │ Create & Optimize│
        └──────┬───────────┘
               │
       ┌───────▼────────┐
       │ Database       │
       │ Tour Creation  │
       └───────┬────────┘
               │
               ▼
      ┌─────────────────┐
      │ Property Visits │
      │ Creation        │
      └───────┬─────────┘
              │
              ▼
      ┌─────────────────┐
      │ Tasks Creation  │
      └───────┬─────────┘
              │
              ▼
      ┌─────────────────┐         ┌────────────────┐
      │ NotificationSvc │         │ CircuitBreaker │
      │ Sync to CRM     │────┬───►│ Protection     │
      └───────┬─────────┘    │    └────────────────┘
              │              │
              ▼              │
      ┌─────────────────┐    │    ┌────────────────┐
      │ RolloutClient   │    └───►│ AlertManager   │
      │ API Calls       │─────────► Error Tracking │
      └───────┬─────────┘         └────────────────┘
              │                            │
              ▼                            ▼
     ┌──────────────────┐         ┌─────────────────┐
     │ External CRM API │         │ Dashboard UI    │
     └──────────────────┘         └─────────────────┘
```

## 8. Service Configuration and Initialization

Services are configured and initialized at application startup:

```
┌───────────────────────────┐
│ Application Startup       │
│ (main.py)                 │
└─────────────┬─────────────┘
              │
┌─────────────▼─────────────┐     ┌────────────────────────────┐
│ Environment Configuration │     │ Configuration Files        │
│ Variables                 │────►│ (config/rollout.env)       │
└─────────────┬─────────────┘     └────────────────────────────┘
              │
┌─────────────▼─────────────┐
│ Database Initialization   │
└─────────────┬─────────────┘
              │
┌─────────────▼─────────────┐
│ API Router Registration   │
└─────────────┬─────────────┘
              │
┌─────────────▼─────────────┐
│ Service Instance Creation │ 
│ (as needed by routes)     │
└─────────────┬─────────────┘
              │
┌─────────────▼─────────────┐
│ Static Files & Templates  │
│ Configuration             │
└───────────────────────────┘
```

## 9. Service Testing Architecture

The services are tested through dedicated test scripts:

```
┌─────────────────────────────────────────────────┐
│              Test Scripts                       │
└────────┬──────────────┬──────────────┬──────────┘
         │              │              │
┌────────▼─────┐ ┌──────▼───────┐ ┌────▼──────────┐
│test_alerts.py│ │test_circuit_ │ │test_monitoring│
│              │ │breaker.py    │ │.py            │
└────────┬─────┘ └──────┬───────┘ └────┬──────────┘
         │              │              │
         │              │              │
┌────────▼─────────────┼──────────────┼────────────┐
│           Mock/Simulated Environment            │
└────────┬──────────────┬──────────────┬──────────┘
         │              │              │
┌────────▼─────┐ ┌──────▼───────┐ ┌────▼──────────┐
│AlertManager  │ │CircuitBreaker│ │Failed         │
│Testing       │ │Testing       │ │Operations Test│
└──────────────┘ └──────────────┘ └───────────────┘
```

This knowledge graph provides a comprehensive view of the service architecture in REanna Router, showing how services interact with each other, the API endpoints, and the data models. The graph also illustrates how data flows through the system and how services are tested.