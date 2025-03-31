# Task Log

## 2025-03-27: CRM Integration Implementation

### Task Description
Implemented a scalable integration strategy for connecting REanna Router with multiple CRM systems (GoHighLevel, Lofty, etc.) using the Rollout API platform.

### Actions Completed
- Analyzed the architectural requirements for CRM integration
- Examined the Rollout API specification to understand capabilities
- Created an MCP server (ID: `e552bffb-b799-4965-9e60-a2bfa664af91`) that provides a unified interface for CRM operations
- Implemented six core tools in the MCP server:
  - `configure_rollout`: Set up connection to Rollout platform
  - `list_available_crms`: List available CRM connectors
  - `configure_crm_connection`: Set up connection to specific CRMs
  - `sync_tour_data`: Sync tour schedules to CRMs
  - `sync_feedback_data`: Sync property feedback to CRMs
  - `create_automation`: Create custom Rollout automations
- Created configuration files for Rollout credentials:
  - Project Key: `proptech`
  - Client ID: `0195d471-6e28-7d24-8eff-0f26ded3a302`
  - Client Secret: [Securely stored]
- Implemented JWT token generation for Rollout API authentication
- Developed a Rollout API client for REanna Router
- Integrated the client with NotificationService to sync feedback to CRMs
- Modified tour routes to include CRM sync capabilities
- Created comprehensive documentation:
  - Strategy document: `roo-notes/crm-integration-strategy.md`
  - Implementation guide: `roo-notes/rollout-integration-guide.md`

### Files Created/Modified
- `config/rollout.env`: Configuration for Rollout credentials
- `app/utils/rollout_auth.py`: JWT token generation for Rollout API
- `app/services/rollout_client.py`: Client for interacting with Rollout API and MCP server
- `app/services/notification_service.py`: Enhanced to support CRM feedback sync
- `app/api/routes/tours.py`: Modified to support tour sync to CRMs
- `roo-notes/crm-integration-strategy.md`: Strategy documentation
- `roo-notes/rollout-integration-guide.md`: Implementation guide

### Challenges and Solutions
- **Challenge**: Needed to support multiple CRMs without bloating the codebase
  - **Solution**: Created an abstraction layer with the MCP server that standardizes CRM interactions
- **Challenge**: Different CRMs have different data models
  - **Solution**: Implemented a flexible data mapping approach in the MCP server
- **Challenge**: Secure credential management
  - **Solution**: Created a dedicated environment file for Rollout credentials

### Follow-up Considerations
- Enhance the MCP server with persistent credential storage
- Add more robust error handling and retry logic
- Implement comprehensive testing for each CRM integration
- Set up monitoring for API usage and rate limits
- Create UI components for managing CRM connections

## 2025-03-27: Enhanced Error Handling and Credential Management Implementation

### Task Description
Implemented robust error handling, retry logic, and secure credential management for the Rollout API integration to improve reliability and security when connecting to CRM systems.

### Actions Completed
- Added dedicated exception classes for different Rollout API error scenarios
- Implemented exponential backoff with jitter for automatic retries
- Added rate limit detection and handling with automatic retry scheduling
- Improved JWT token management with automatic refreshing and expiry tracking
- Created a secure credential storage utility for encrypting sensitive API keys
- Updated notification service to handle retries for failed CRM syncs
- Enhanced tour routes to gracefully handle CRM sync failures
- Developed a test script for demonstrating retry logic and error handling
- Created a to-do list for future error handling enhancements

### Files Created/Modified
- `app/services/rollout_client.py`: Added retry logic, error handling, and rate limiting support
- `app/utils/rollout_auth.py`: Enhanced JWT token generation with better error handling
- `app/services/notification_service.py`: Updated to handle errors and retry operations
- `app/api/routes/tours.py`: Enhanced to handle sync failures gracefully
- `app/utils/credential_store.py`: New file for secure credential management
- `scripts/test_rollout_integration.py`: New test script for demonstrating error handling
- `roo-notes/todo-crm-error-handling.md`: Task list for error handling implementation

### Challenges and Solutions
- **Challenge**: Different error types require different retry strategies
  - **Solution**: Created specialized exception classes and tailored retry logic
- **Challenge**: Rate limiting can block operations for extended periods
  - **Solution**: Implemented background retry scheduling with appropriate delays
- **Challenge**: Secure storage of API credentials
  - **Solution**: Created an encrypted storage system with proper permission management
- **Challenge**: Adding robust error handling without cluttering code
  - **Solution**: Used structured try/except blocks with specific exception types

### Follow-up Considerations
- Implement a monitoring system for tracking API usage and rate limits
- Create an admin dashboard for viewing sync status and manually retrying failed operations
- Set up automated alerts for repeated sync failures
- Add comprehensive unit tests for error handling scenarios
- Implement the circuit breaker pattern for Rollout API calls to prevent cascading failures
- Develop a metrics collection system for API performance tracking

## 2025-03-28: Circuit Breaker Pattern Implementation

### Task Description
Implemented the circuit breaker pattern for Rollout API and MCP server calls to prevent cascading failures and improve system resilience when external services experience issues.

### Actions Completed
- Created a generic CircuitBreaker utility class with configurable thresholds and recovery timeouts
- Implemented three circuit states: CLOSED (normal operation), OPEN (blocking calls), and HALF-OPEN (testing recovery)
- Integrated circuit breakers with the Rollout client for both API and MCP server calls
- Added a new RolloutCircuitOpenError exception type for circuit breaker failures
- Updated the notification service to handle circuit breaker errors gracefully
- Enhanced tour routes to properly handle circuit open states
- Created a test script to demonstrate circuit breaker functionality
- Updated documentation to reflect the circuit breaker implementation

### Files Created/Modified
- `app/utils/circuit_breaker.py`: New file implementing the generic circuit breaker pattern
- `app/services/rollout_client.py`: Updated to use circuit breakers for API and MCP calls
- `app/services/notification_service.py`: Enhanced to handle circuit breaker errors
- `app/api/routes/tours.py`: Updated to handle circuit open states in sync operations
- `scripts/test_circuit_breaker.py`: Created test script to demonstrate functionality
- `roo-notes/error-handling-summary.md`: Updated documentation with circuit breaker details
- `roo-notes/todo-crm-error-handling.md`: Updated to mark circuit breaker task as completed

### Challenges and Solutions
- **Challenge**: Determining appropriate failure thresholds for different operations
  - **Solution**: Used different thresholds for API calls (3) and MCP calls (5) based on reliability characteristics
- **Challenge**: Preventing rate limit errors from triggering the circuit breaker
  - **Solution**: Implemented excluded exception list in the circuit breaker design
- **Challenge**: Ensuring proper recovery from open circuit state
  - **Solution**: Used a half-open state with limited test calls to verify service recovery

### Follow-up Considerations
- Add monitoring for circuit breaker state changes
- Implement dashboard elements to visualize circuit breaker states
- Consider implementing metrics collection for analyzing circuit breaker effectiveness
- Add alarms for persistent circuit open conditions

## 2025-03-28: API Monitoring System Implementation

### Task Description
Implemented a comprehensive monitoring system for tracking API usage, rate limits, circuit breaker states, and performance metrics for the Rollout API integration, providing visibility into the operational health of the CRM integration.

### Actions Completed
- Created a monitoring module with classes for tracking various metrics:
  - API call statistics (success counts, error counts, response times)
  - Rate limit consumption and reset times
  - Circuit breaker state transitions and failure tracking
  - Performance metrics collection with percentile calculations
- Implemented context managers for API calls to simplify metrics collection
- Enhanced the circuit breaker implementation to report state changes to the monitoring system
- Updated the Rollout client to use the monitoring system for all API and MCP calls
- Designed the monitoring system to provide key operational visibility metrics:
  - Success/failure rates for each API endpoint
  - Response time statistics including 95th percentile measurements
  - Rate limit consumption patterns to prevent service disruptions
  - Circuit breaker state changes for detecting failing services
- Created new API endpoints for accessing monitoring data:
  - `/api/monitoring/api-stats`: Get API usage statistics
  - `/api/monitoring/rate-limits`: Get rate limit information
  - `/api/monitoring/circuit-states`: Get circuit breaker states
  - `/api/monitoring/summary`: Get a comprehensive health summary
- Developed testing infrastructure:
  - Created `scripts/test_monitoring.py` to verify full monitoring integration
  - Created `scripts/test_monitoring_standalone.py` as a dependency-isolated test
  - Updated testing documentation to follow best practices

### Files Created/Modified
- `app/utils/monitoring.py`: New file implementing the monitoring system
- `app/utils/circuit_breaker.py`: Updated to integrate with monitoring
- `app/services/rollout_client.py`: Enhanced to use monitoring context managers
- `app/api/routes/monitoring.py`: New API endpoints for accessing monitoring data
- `app/api/routes/__init__.py`: Updated to include monitoring router
- `app/main.py`: Updated to register monitoring router
- `scripts/test_monitoring.py`: New test script for integrated testing
- `scripts/test_monitoring_standalone.py`: Standalone test script for isolated testing
- `roo-notes/todo-crm-error-handling.md`: Updated to reflect completed tasks
- `roo-notes/remember.md`: Added section on testing best practices and dependency management

### Challenges and Solutions
- **Challenge**: Monitoring API calls without cluttering client code
  - **Solution**: Implemented context managers that automatically track metrics
- **Challenge**: Efficiently tracking circuit breaker state changes
  - **Solution**: Added tracking calls at all state transition points
- **Challenge**: Providing a clear health status overview
  - **Solution**: Created a summary endpoint that aggregates and analyzes metrics
- **Challenge**: Handling dependencies in test scripts
  - **Solution**: Created standalone test script that doesn't rely on application infrastructure
- **Challenge**: Managing Python module dependencies
  - **Solution**: Updated dependency handling practices and requirements.txt

### Follow-up Considerations
- Create a web dashboard UI for visualizing monitoring data
- Implement automatic alerts based on monitoring thresholds
- Add historical metrics storage for trend analysis
- Extend monitoring to include detailed operation-specific metrics
- Create comprehensive test suite with PyTest for all components
- Add unit tests for critical monitoring functions
- Set up continuous integration testing for the monitoring system
- Implement log aggregation to centralize monitoring data
- Consider using a time-series database for long-term metrics storage

## 2025-03-28: CRM Integration Monitoring Dashboard Implementation

### Task Description
Implemented a comprehensive web dashboard for monitoring CRM integration health, API usage metrics, circuit breaker states, and managing failed operations, providing operators with a user-friendly interface to track system performance and troubleshoot integration issues.

### Actions Completed
- Created an interactive web dashboard with five main sections:
  - System overview with health status and key metrics
  - Detailed API statistics with sorting and filtering
  - Circuit breaker visualization with state tracking
  - Rate limits monitoring with usage percentages
  - Failed operations management with retry capabilities
- Developed responsive frontend components:
  - Created HTML templates with Jinja2 integration
  - Designed a clean, responsive CSS layout
  - Implemented interactive JavaScript functionality
  - Added Chart.js visualizations for metrics
- Extended backend functionality:
  - Added API endpoints for failed operations management
  - Created route handler for serving dashboard
  - Set up static file serving for CSS and JavaScript
  - Integrated FastAPI templates with static assets
- Implemented operational capabilities:
  - Real-time system health monitoring
  - Failed operation retry functionality
  - Rate limit visualization and tracking
  - Circuit breaker state management
  - Performance metrics visualization
- Created a dashboard testing script to demonstrate functionality

### Files Created/Modified
- `app/templates/base.html`: Base HTML template with responsive layout
- `app/templates/dashboard.html`: Main dashboard template with all sections
- `app/static/css/styles.css`: Comprehensive CSS styling for the dashboard
- `app/static/js/dashboard.js`: Interactive JavaScript with charts and data fetching
- `app/api/routes/dashboard.py`: Route handler for serving dashboard pages
- `app/api/routes/monitoring.py`: Enhanced with failed operations endpoints
- `app/api/routes/__init__.py`: Updated to include dashboard router
- `app/main.py`: Modified to support static files and dashboard routing
- `scripts/test_dashboard.py`: Test script for dashboard functionality

### Challenges and Solutions
- **Challenge**: Visualizing complex system health data in an intuitive way
  - **Solution**: Used color-coded indicators and charts to provide at-a-glance status
- **Challenge**: Managing failed operations without a persistent database
  - **Solution**: Implemented in-memory storage with complete CRUD operations
- **Challenge**: Creating responsive design that works on different devices
  - **Solution**: Used a flexible grid layout with breakpoints for various screen sizes
- **Challenge**: Integrating real-time data updates without overwhelming the server
  - **Solution**: Implemented configurable refresh intervals with efficient API calls

### Follow-up Considerations
- Implement persistent storage for failed operations
- Add email or Slack notifications for critical alerts
- Implement historical data tracking for trend analysis
- Add user authentication for the dashboard
- Develop custom widgets for specific monitoring needs
- Create printable/exportable reports for system health
- Implement WebSocket for real-time updates instead of polling
- Add customizable dashboard layouts for different user roles

## 2025-03-28: Database Dependencies Refactoring and CRM Integration Future Planning

### Task Description
Refactored database dependencies to improve system architecture, created a standalone dashboard demo, and developed a comprehensive plan for future CRM integrations using the Rollout API platform and GoHighLevel Connector.

### Actions Completed
- Refactored database dependencies:
  - Removed explicit Database type annotations from route handler parameters
  - Updated dependency injection in tours.py and other API routes
  - Modified notification service to properly handle database connections
  - Fixed type issues and documentation to reflect the changes
- Added missing model components:
  - Created TourStatus enum for standardized status management
  - Implemented the TourResponse model with sync status fields
  - Updated existing code to use the new models
- Created a standalone dashboard demo:
  - Developed a self-contained dashboard without external dependencies
  - Implemented a pure HTML/CSS/JS frontend with embedded mock data
  - Created API endpoints for accessing monitoring information
  - Built a simplified server that runs independently
- Developed future CRM integration plans:
  - Analyzed the GoHighLevel Calendars API for integration opportunities
  - Created detailed documentation on Rollout API automation capabilities
  - Documented integration paths for contacts, conversations, and calendar management
  - Outlined a three-phase implementation approach
  - Created example payload structures for key integration points

### Files Created/Modified
- `app/api/routes/tours.py`: Updated database dependencies and route handlers
- `app/services/notification_service.py`: Modified to use updated database approach
- `app/models/tour.py`: Added TourStatus enum and TourResponse class
- `scripts/simple_dashboard_demo.py`: Created standalone dashboard demo
- `roo-notes/rollout-future-integrations.md`: New document outlining future integration plans

### Challenges and Solutions
- **Challenge**: Removing typed database dependencies without breaking functionality
  - **Solution**: Carefully refactored each route handler to maintain compatibility
- **Challenge**: Running the dashboard demo with minimal dependencies
  - **Solution**: Created a self-contained demo using FastAPI's built-in HTML response
- **Challenge**: Understanding the complex Rollout and GoHighLevel API ecosystem
  - **Solution**: Analyzed API specs and created a comprehensive integration plan

### Follow-up Considerations
- Implement GoHighLevel calendar integration using the Rollout API connector
- Develop contact synchronization between REanna Router and CRM systems
- Create automated messaging workflows for tour notifications and feedback
- Implement connector-specific monitoring in the dashboard
- Extend the MCP server with tools specific to each CRM system
- Develop a CRM schema analyzer for mapping data between systems
- Create data validation tools to ensure consistency across integrations

## 2025-03-28: Alert System Implementation for Repeated Sync Failures

### Task Description
Implemented a comprehensive alert system for detecting and notifying about repeated sync failures, circuit breaker open events, and other critical integration issues. The system provides configurable thresholds, multiple notification methods, and integrates with the monitoring dashboard for visualizing alerts.

### Actions Completed
- Created a flexible AlertManager utility class with:
  - Support for different alert types (REPEATED_SYNC_FAILURE, CIRCUIT_BREAKER_OPEN, RATE_LIMIT_CRITICAL, etc.)
  - Configurable alert thresholds, time windows, and cooldown periods
  - Multiple notification methods (LOG, EMAIL, WEBHOOK, SLACK)
  - Failure tracking with time-windowed threshold analysis
- Integrated alert detection into the notification service:
  - Added alert triggering for repeated sync failures
  - Added alert triggering for circuit breaker open events
  - Added alert triggering for rate limit critical conditions
- Enhanced the monitoring dashboard with:
  - New "Alerts" section showing recent triggered alerts
  - Alert configuration management UI
  - Test notification functionality
  - Visual indicators for active alerts
- Created REST API endpoints for alert management:
  - `/api/monitoring/alerts` for retrieving alerts
  - `/api/monitoring/alert-configs` for getting and updating alert configurations
  - `/api/monitoring/test-alert` for testing notification delivery
- Developed a test script to demonstrate the alert system functionality

### Files Created/Modified
- `app/utils/alert_manager.py`: New utility for alerting on repeated failures
- `app/services/notification_service.py`: Updated to integrate with alert system
- `app/api/routes/monitoring.py`: Added new endpoints for alert management
- `app/templates/dashboard.html`: Added alerts section UI
- `app/static/js/dashboard.js`: Added JavaScript for fetching and displaying alerts
- `app/static/css/styles.css`: Added styles for alert components
- `scripts/test_alert_system.py`: Created test script for alert functionality

### Challenges and Solutions
- **Challenge**: Determining appropriate thresholds for alerts
  - **Solution**: Made thresholds configurable per alert type with reasonable defaults
- **Challenge**: Avoiding alert storms for related failures
  - **Solution**: Implemented cooldown periods for each entity+alert type combination
- **Challenge**: Supporting multiple notification methods
  - **Solution**: Created an extensible design with pluggable notification handlers
- **Challenge**: Designing a clean UI for alert management
  - **Solution**: Created a dedicated dashboard section with clear visual indicators

### Follow-up Considerations
- Implement persistent storage for alerts history
- Add more sophisticated notification methods (SMS, mobile push)
- Implement alert aggregation to reduce notification volume
- Create alert severity escalation based on duration
- Develop alert templates for different notification methods
- Add support for custom alerting rules based on specific error patterns
- Implement scheduled health check alerts

## 2025-03-28: Knowledge Graph Documentation of Application Architecture

### Task Description
Created a comprehensive knowledge graph documentation of the REanna Router application architecture, starting with main.py as the central component and mapping all relationships between components throughout the system.

### Actions Completed
- Created a set of detailed knowledge graph documentation files:
  - `roo-notes/application-architecture-knowledge-graph.md`: Overview of the entire application structure
  - `roo-notes/services-architecture-knowledge-graph.md`: Detailed mapping of service interactions
  - `roo-notes/error-handling-knowledge-graph.md`: Complete error flow documentation and circuit breaker patterns
  - `roo-notes/alert-system-knowledge-graph.md`: Documentation of the alert system components
  - `roo-notes/reanna-router-knowledge-graph-index.md`: Central index connecting all documents
- Used MCP_DOCKER tools to build the knowledge graph:
  - Created entities representing modules, classes, and components
  - Established relationships between entities to show imports, dependencies, and data flow
  - Built a comprehensive connected graph showing app architecture
- Enhanced test scripts with improved logging and documentation
- Added ASCII diagrams showing architectural relationships and data flows
- Created indexed documentation for easy navigation across architecture components

### Files Created/Modified
- `roo-notes/application-architecture-knowledge-graph.md`: High-level system architecture
- `roo-notes/services-architecture-knowledge-graph.md`: Service layer mapping
- `roo-notes/error-handling-knowledge-graph.md`: Error handling flow documentation
- `roo-notes/alert-system-knowledge-graph.md`: Alert system documentation
- `roo-notes/reanna-router-knowledge-graph-index.md`: Central index with system overview
- `roo-notes/alert-system-documentation.md`: Comprehensive documentation of the alert system
- `scripts/test_alerts.py`: Enhanced with improved structured logging

### Challenges and Solutions
- **Challenge**: Representing complex architecture relationships in a digestible format
  - **Solution**: Used the MCP_DOCKER knowledge graph tools to create entities and relationships
- **Challenge**: Organizing large amounts of architectural information
  - **Solution**: Split documentation into logical modules with a central index
- **Challenge**: Visualizing component interactions without advanced diagramming tools
  - **Solution**: Created detailed ASCII diagrams to show relationships and flows
- **Challenge**: Documenting both static structure and dynamic behavior
  - **Solution**: Created separate diagrams for static relationships and data flow sequences

### Follow-up Considerations
- Consider a production-ready database solution:
  - **Apache Cassandra**: High scalability, distributed NoSQL database suited for high write throughput
  - **MongoDB**: Flexible document-based NoSQL database with strong horizontal scaling capabilities
  - **PostgreSQL**: Robust relational database with strong ACID compliance and JSON support
- Determine appropriate messaging and caching solutions based on database choice:
  - **With Apache Cassandra**: Apache Pulsar for messaging, which works well in the same ecosystem
  - **With MongoDB**: Redis for caching and Celery workers for task queues, or Kafka for messaging
  - **With PostgreSQL**: Similar Redis/Celery combination or Kafka, with PostgREST for API layer
- Implement persistent storage for monitoring data and historical metrics
- Create data migration strategy for moving from SQLite to production database
- Design sharding or partitioning strategy based on expected data growth patterns
- Implement connection pooling for improved database performance
- Consider using an ORM like SQLAlchemy for better database abstraction
- Develop a backup and disaster recovery strategy
- Implement database monitoring and performance tuning
- Evaluate security requirements for database access and encryption
- Create database schema version control strategy

## 2025-03-28: Database Implementation Planning for Production

### Task Description
Developed a comprehensive implementation plan for migrating REanna Router from SQLite to production-ready Supabase (PostgreSQL) and Upstash Redis, deployed on Railway using Docker containers, with an optional webhook router service for enhanced integration capabilities.

### Actions Completed
- Created a detailed database implementation plan with the following components:
  - Supabase (PostgreSQL) schema design for all core data models
  - Upstash Redis implementation for caching, circuit breakers, and rate limiting
  - Webhook router service architecture design for decoupled integration
  - Complete migration strategy from SQLite to Supabase
  - Railway deployment configuration using Docker
  - Implementation timeline across five phases
- Designed a comprehensive PostgreSQL schema:
  - Enhanced existing models with additional fields for CRM sync status
  - Created new tables for monitoring and metrics
  - Developed a robust indexing strategy
  - Implemented row-level security patterns
- Developed Redis cache strategy:
  - Defined cache key structure and naming conventions
  - Created caching implementations for dashboard data
  - Designed circuit breaker state management in Redis
  - Implemented rate limit tracking using Redis sorted sets
  - Established pub/sub patterns for alerts and notifications
- Designed webhook router architecture:
  - Created webhook endpoint design
  - Developed event normalization strategies
  - Implemented Redis Streams for reliable event processing
  - Designed provider-specific handlers for different CRM systems
- Outlined a phased migration approach:
  - Preparation and schema creation
  - Initial and incremental data migration
  - Cutover strategy and rollback planning
  - Deployment configuration for Railway

### Files Created/Modified
- `roo-notes/database-implementation-plan.md`: Comprehensive database migration and implementation plan

### Challenges and Solutions
- **Challenge**: Designing a schema that preserves existing functionality while enabling new features
  - **Solution**: Enhanced the current model with additional fields while maintaining compatibility
- **Challenge**: Creating an effective caching strategy that works across different components
  - **Solution**: Developed a standardized cache key structure and consistent patterns
- **Challenge**: Developing a reliable migration approach with minimal downtime
  - **Solution**: Created a phased migration strategy with verification steps and rollback options
- **Challenge**: Designing a webhook router that can handle various external API formats
  - **Solution**: Implemented a provider-specific normalization approach with a standardized internal event format
- **Challenge**: Ensuring proper security for database access in production
  - **Solution**: Designed row-level security policies for Supabase

### Follow-up Considerations
- Implement the schema design in a Supabase development environment
- Develop migration tools with data verification functionality
- Create a prototype webhook router service
- Set up continuous integration for schema changes
- Design backup and disaster recovery processes for production data
- Develop monitoring dashboards for database performance
- Create comprehensive testing for database operations
- Implement database connection pooling for optimal performance
- Design database versioning and migration strategies

## 2025-03-30: Code Fixes and Dependency Updates

### Task Description
Fixed various code errors and dependency issues to ensure smooth operation of the REanna Router integration components and testing scripts.

### Actions Completed
- Added the `cryptography` package to requirements.txt to fix missing imports in credential_store.py
- Fixed `web` undefined error in test_alert_system.py by properly importing aiohttp web module
- Fixed `WebhookConfig` undefined error in test_alert_system.py by adding it to imports
- Added a default endpoint value in rollout_client.py to resolve the undefined endpoint issue
- Verified test scripts run successfully after fixes

### Files Created/Modified
- `requirements.txt`: Added cryptography package dependency
- `scripts/test_alert_system.py`: Fixed missing imports for web and WebhookConfig
- `app/services/rollout_client.py`: Added default endpoint value for rate limit tracking

### Challenges and Solutions
- **Challenge**: Missing cryptography module causing credential store to fail
  - **Solution**: Added cryptography package to requirements.txt
- **Challenge**: Undefined variables in test scripts preventing successful test runs
  - **Solution**: Added proper imports and variable definitions
- **Challenge**: Missing parameter in rate limiting code leading to undefined variable
  - **Solution**: Added default value for endpoint parameter

### Follow-up Considerations
- Review all test scripts for similar missing dependencies or imports
- Consider adding automated dependency checks to CI/CD pipeline
- Add more explicit error handling for missing dependencies
- Create comprehensive test coverage for all components
- Consider using a virtual environment management tool like Poetry for better dependency management
