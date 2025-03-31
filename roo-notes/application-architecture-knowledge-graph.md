# REanna Router Application Architecture Knowledge Graph

This document maps the complete architecture of the REanna Router system with main.py as the central component. The knowledge graph shows how components connect and interact across the application.

## 1. Application Entry Point (main.py)

`main.py` serves as the entry point for the REanna Router application, initializing all core components and connecting the various parts of the system.

```
┌───────────────────────────────────────────────────────────────┐
│                          main.py                              │
│                                                               │
│  ┌───────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ FastAPI App   │  │ CORS Config  │  │ Static Files Mount │  │
│  │ Configuration │  │ Middleware   │  │ for Dashboard      │  │
│  └───────────────┘  └──────────────┘  └────────────────────┘  │
│                                                               │
│           ┌──────────────────────────────────────┐            │
│           │         Router Registration          │            │
│           └──────────────────────────────────────┘            │
│                                                               │
│  ┌───────────────┐  ┌──────────────┐  ┌────────────────────┐  │
│  │ Health Check  │  │ Legacy API   │  │ Root Endpoint      │  │
│  │ Endpoint      │  │ Compatibility │  │ Documentation      │  │
│  └───────────────┘  └──────────────┘  └────────────────────┘  │
└───────────────────────────────────────────────────────────────┘
```

### Key Components:

* **FastAPI App Configuration**: Sets up the main application with title, description, version
* **Router Registration**: Connects all API routers to the main application
* **Legacy API Compatibility**: `optimize_legacy` endpoint maintains compatibility with older clients
* **Static Files Mount**: Serves dashboard assets like CSS and JavaScript

## 2. API Routes Structure

The application is organized around several domain-specific API routers:

```
┌─────────────────────────────────────┐
│              main.py                │
└─────────────────┬───────────────────┘
                  │ includes
                  ▼
┌─────────────────────────────────────┐
│         api/routes/__init__.py      │
└───────┬─────┬─────┬─────┬─────┬─────┘
        │     │     │     │     │
        ▼     ▼     ▼     ▼     ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│ tours │ │ tasks │ │feedback│ │property│ │monitor│
│ router│ │ router│ │ router│ │ visits │ │ router│
└───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘ └───┬───┘
    │         │         │         │         │
    ▼         ▼         ▼         ▼         ▼
┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
│ Tour  │ │ Task  │ │Feedback│ │Property│ │Dashboard
│ Model │ │ Model │ │ Model │ │ Visit  │ │ UI    │
└───────┘ └───────┘ └───────┘ └───────┘ └───────┘
```

### Router Dependencies:

* **tours_router**: Depends on Tour Model, OptimizationService, NotificationService
* **tasks_router**: Depends on Task Model, Property Visit Model
* **feedback_router**: Depends on Feedback Model, NotificationService
* **property_visits_router**: Depends on Property Visit Model
* **monitoring_router**: Depends on AlertManager, CircuitBreaker
* **dashboard_router**: Depends on Jinja2Templates, monitoring data

## 3. Data Models and Database

The application's data is organized around four primary models:

```
┌───────────────────────────────────────┐
│          Database Module              │
│ (SQLite with contextual connections)  │
└───────────────────┬───────────────────┘
                    │
         ┌──────────┴───────────┐
         │                      │
┌────────▼─────────┐   ┌────────▼─────────┐
│    Tour Model    │   │ Property Visit   │
│                  │   │     Model        │
└────────┬─────────┘   └────────┬─────────┘
         │                      │
         │                      │
         │             ┌────────▼─────────┐
         │             │    Task Model    │
         │             │                  │
         │             └────────┬─────────┘
         │                      │
         │                      │
         │             ┌────────▼─────────┐
         │             │  Feedback Model  │
         │             │                  │
         │             └──────────────────┘
         │
         │
┌────────▼─────────┐
│   TourStatus     │
│      Enum        │
└──────────────────┘
```

### Model Relationships:

* **Tour** contains many **Property Visits**
* **Property Visit** contains many **Tasks**
* **Task** may have **Feedback** (especially for feedback_collection task type)
* All models use the **Database Module** for persistence
* **TourStatus** enum defines possible states for a Tour

## 4. Services Architecture

The application's business logic is organized into several services:

```
┌────────────────────────┐      ┌────────────────────────┐
│  OptimizationService   │      │  NotificationService   │
│                        │      │                        │
│ - Route planning       │      │ - Agent notifications  │
│ - Visit scheduling     │      │ - Feedback processing  │
│ - Google Maps API      │      │ - CRM integration      │
└──────────┬─────────────┘      └────────────┬───────────┘
           │                                  │
           │creates                           │uses
           │                                  │
┌──────────▼─────────────┐      ┌─────────────▼──────────┐
│                        │      │                        │
│   Property Visits      │      │    RolloutClient       │
│                        │      │                        │
└──────────┬─────────────┘      └────────────┬───────────┘
           │                                  │
           │                                  │uses
           │creates                           │
┌──────────▼─────────────┐      ┌─────────────▼──────────┐
│                        │      │                        │
│       Tasks            │      │    CircuitBreaker      │
│                        │      │                        │
└────────────────────────┘      └────────────┬───────────┘
                                              │
                                              │notifies
                                              │
                                ┌─────────────▼──────────┐
                                │                        │
                                │    AlertManager        │
                                │                        │
                                └────────────────────────┘
```

### Service Responsibilities:

* **OptimizationService**: Creates and optimizes property visit schedules
* **NotificationService**: Handles notifications and CRM integration
* **RolloutClient**: Manages API calls to external CRM services
* **CircuitBreaker**: Prevents cascading failures in external API calls
* **AlertManager**: Detects patterns and sends notifications for issues

## 5. Monitoring and Alert System

The monitoring system provides visibility into the application's health:

```
┌───────────────────────────────────────────┐
│             monitoring_router             │
└─────────────────────┬─────────────────────┘
                      │
           ┌──────────┴──────────┐
           │                     │
┌──────────▼─────────┐ ┌─────────▼──────────┐
│   API Statistics   │ │    Failed          │
│   Endpoints        │ │    Operations      │
└──────────┬─────────┘ └─────────┬──────────┘
           │                     │
           │                     │             ┌───────────────────┐
┌──────────▼─────────┐           │             │  alert_manager.py │
│  Rate Limit        │           └─────────────► - AlertLevel      │
│  Monitoring        │                         │ - AlertType       │
└──────────┬─────────┘                         │ - AlertMethod     │
           │                                   │ - AlertConfig     │
           │                                   └─────────┬─────────┘
┌──────────▼─────────┐                                   │
│  Circuit Breaker   │                                   │
│  State Tracking    ├───────────────────────────────────┘
└────────────────────┘
```

### Monitoring Components:

* **API Statistics Endpoints**: Track API usage, response times, error rates
* **Failed Operations Tracking**: Record and display operation failures
* **Rate Limit Monitoring**: Track API rate limit consumption
* **Circuit Breaker State Tracking**: Monitor open/closed circuit states
* **AlertManager**: Central component for detecting and notifying about issues

## 6. Dashboard and User Interface

The dashboard provides visualization of system status:

```
┌─────────────────────────┐      ┌─────────────────────────┐
│   dashboard_router      │      │   dashboard.html        │
│                         │──────►                         │
└─────────────┬───────────┘      └───────────┬─────────────┘
              │                              │
              │uses                          │includes
              │                              │
┌─────────────▼───────────┐    ┌─────────────▼─────────────┐
│   Jinja2Templates        │    │   dashboard.js           │
└───────────────────────┬─┘    └─────────────┬─────────────┘
                        │                     │
                        │renders              │fetches data from
                        │                     │
┌───────────────────────▼─┐   ┌──────────────▼──────────────┐
│   templates/            │   │   monitoring_router         │
│   base.html             │   │   endpoints                 │
└─────────────────────────┘   └─────────────────────────────┘
```

### Dashboard Components:

* **dashboard_router**: Serves the HTML template for the dashboard
* **Jinja2Templates**: Renders the HTML with data
* **dashboard.js**: Client-side JavaScript for interactive features
* **monitoring_router endpoints**: Provide data for the dashboard

## 7. Full System Data Flow

The complete system's data flow follows this pattern:

```
┌──────────────┐
│ Tour Creation│
│ (API Request)│
└──────┬───────┘
       │
       ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ tours_router │────►│ Optimization │────►│Property Visits│
└──────┬───────┘     │ Service      │     │ Creation     │
       │             └──────────────┘     └──────┬───────┘
       │                                         │
       │                                         ▼
       │                                  ┌──────────────┐
       │                                  │  Tasks       │
       │                                  │  Creation    │
       │                                  └──────┬───────┘
       │                                         │
       │                                         │
       ▼                                         ▼
┌──────────────┐     ┌──────────────┐    ┌──────────────┐
│ Notification │     │ Rollout      │    │ Feedback     │
│ Service      │────►│ Client       │    │ Collection   │
└──────┬───────┘     └──────┬───────┘    └──────┬───────┘
       │                    │                   │
       │                    ▼                   ▼
       │            ┌──────────────┐    ┌──────────────┐
       │            │Circuit Breaker│    │ Notification │
       │            │ Protection    │    │ to Agent     │
       │            └──────┬───────┘    └──────────────┘
       │                   │
       ▼                   ▼
┌──────────────┐    ┌──────────────┐     ┌──────────────┐
│ Alert        │◄───┤ Failed       │────►│ Dashboard    │
│ Manager      │    │ Operations   │     │ Display      │
└──────────────┘    └──────────────┘     └──────────────┘
```

## 8. Main Application Structure

The main.py file serves as the coordination point for the entire application, pulling together all components:

```
                    ┌───────────────┐
                    │    main.py    │
                    └───────┬───────┘
                            │
         ┌──────────────────┼──────────────────┐
         │                  │                  │
┌────────▼────────┐ ┌───────▼────────┐ ┌───────▼────────┐
│ API Routes      │ │ Database       │ │Static Files    │
│ Registration    │ │ Initialization │ │Configuration   │
└────────┬────────┘ └───────┬────────┘ └───────┬────────┘
         │                  │                  │
┌────────▼────────┐ ┌───────▼────────┐ ┌───────▼────────┐
│tours_router     │ │ Models:        │ │ Dashboard UI   │
│tasks_router     │ │ - Tour         │ │ Assets:        │
│feedback_router  │ │ - Property Visit│ │ - CSS         │
│property_visits_ │ │ - Task         │ │ - JavaScript   │
│router           │ │ - Feedback     │ │ - Templates    │
│monitoring_router│ └────────────────┘ └────────────────┘
└────────┬────────┘
         │
┌────────▼────────┐
│ Services:       │
│ - Optimization  │
│ - Notification  │
│ - Rollout Client│
│ - Alert Manager │
│ - Circuit Breaker│
└─────────────────┘
```

This knowledge graph provides a comprehensive view of the REanna Router architecture, showing how all components connect through main.py as the central coordination point.