# Database Implementation Plan: Supabase and Upstash Redis

## 1. Introduction

### 1.1 Purpose

This document outlines a comprehensive plan for migrating REanna Router from SQLite to a production-ready database architecture using Supabase (PostgreSQL) and Upstash Redis, deployed on Railway using Docker.

### 1.2 Current State

REanna Router currently uses SQLite for data persistence with the following characteristics:

- Simple file-based database suited for development
- Relational data model with Tours → PropertyVisits → Tasks → Feedback
- No separate caching layer
- Limited concurrency capabilities
- Recently enhanced with monitoring, alerts, and CRM integration

### 1.3 Target Architecture

The target architecture consists of:

- **Supabase**: Managed PostgreSQL database for persistent storage
- **Upstash Redis**: Serverless Redis for caching, rate limiting, and real-time features
- **Railway**: PaaS hosting with Docker support
- **Webhook Router Service**: Optional new component for enhanced integration capabilities

## 2. Supabase Database Implementation

### 2.1 Schema Design

#### 2.1.1 Core Tables

Migrating the existing schema to Supabase will maintain the current relational structure:

- **tours**

  ```sql
  CREATE TABLE tours (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,
    start_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    status TEXT NOT NULL,
    route_data JSONB,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    crm_sync_status TEXT DEFAULT 'not_synced',
    crm_sync_timestamp TIMESTAMP WITH TIME ZONE,
    crm_sync_error TEXT
  );
  ```

- **property_visits**

  ```sql
  CREATE TABLE property_visits (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tour_id UUID REFERENCES tours(id) ON DELETE CASCADE,
    address TEXT NOT NULL,
    property_id TEXT,
    scheduled_arrival TIMESTAMP WITH TIME ZONE NOT NULL,
    scheduled_departure TIMESTAMP WITH TIME ZONE NOT NULL,
    actual_arrival TIMESTAMP WITH TIME ZONE,
    actual_departure TIMESTAMP WITH TIME ZONE,
    status TEXT NOT NULL,
    sellside_agent_id TEXT,
    sellside_agent_name TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
  );
  ```

- **tasks**

  ```sql
  CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    visit_id UUID REFERENCES property_visits(id) ON DELETE CASCADE,
    task_type TEXT NOT NULL,
    status TEXT NOT NULL,
    scheduled_time TIMESTAMP WITH TIME ZONE NOT NULL,
    completed_time TIMESTAMP WITH TIME ZONE,
    shipment_id TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
  );
  ```

- **feedback**

  ```sql
  CREATE TABLE feedback (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    raw_feedback TEXT NOT NULL,
    processed_feedback TEXT,
    feedback_source TEXT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    sent_to_agent BOOLEAN DEFAULT FALSE,
    notification_attempts INTEGER DEFAULT 0,
    last_notification_attempt TIMESTAMP WITH TIME ZONE,
    notification_error TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
  );
  ```

#### 2.1.2 Monitoring and Alert Tables

New tables to support the monitoring and alert features:

- **api_metrics**

  ```sql
  CREATE TABLE api_metrics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    endpoint TEXT NOT NULL,
    method TEXT NOT NULL,
    status_code INTEGER NOT NULL,
    response_time FLOAT NOT NULL,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    success BOOLEAN NOT NULL,
    error_type TEXT,
    error_message TEXT
  );
  ```

- **circuit_breaker_events**

  ```sql
  CREATE TABLE circuit_breaker_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    service_name TEXT NOT NULL,
    previous_state TEXT NOT NULL,
    new_state TEXT NOT NULL,
    failure_count INTEGER,
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    reason TEXT
  );
  ```

- **alerts**

  ```sql
  CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alert_type TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    message TEXT NOT NULL,
    severity TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'active',
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    resolved_at TIMESTAMP WITH TIME ZONE,
    notification_sent BOOLEAN DEFAULT FALSE
  );
  ```

### 2.2 Indexing Strategy

Indexes to optimize query performance:

```sql
-- Tour queries
CREATE INDEX idx_tours_agent_id ON tours(agent_id);
CREATE INDEX idx_tours_status ON tours(status);
CREATE INDEX idx_tours_date_range ON tours(start_time, end_time);
CREATE INDEX idx_tours_crm_sync_status ON tours(crm_sync_status);

-- Property visit queries
CREATE INDEX idx_property_visits_tour_id ON property_visits(tour_id);
CREATE INDEX idx_property_visits_status ON property_visits(status);
CREATE INDEX idx_property_visits_scheduled_time ON property_visits(scheduled_arrival);

-- Task queries
CREATE INDEX idx_tasks_visit_id ON tasks(visit_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_type ON tasks(task_type);

-- Feedback queries
CREATE INDEX idx_feedback_task_id ON feedback(task_id);
CREATE INDEX idx_feedback_sent_status ON feedback(sent_to_agent);

-- Metrics and monitoring
CREATE INDEX idx_api_metrics_endpoint ON api_metrics(endpoint, method);
CREATE INDEX idx_api_metrics_timestamp ON api_metrics(timestamp);
CREATE INDEX idx_circuit_breaker_service ON circuit_breaker_events(service_name);
CREATE INDEX idx_alerts_type ON alerts(alert_type);
CREATE INDEX idx_alerts_status ON alerts(status);
CREATE INDEX idx_alerts_entity ON alerts(entity_type, entity_id);
```

### 2.3 Data Types and Optimizations

- Using `UUID` as primary key type for distributed scalability
- Storing JSON data in `JSONB` format for better query performance
- Adding `created_at` and `updated_at` timestamps for all tables
- Using `TIMESTAMP WITH TIME ZONE` for all datetime fields

### 2.4 Row-Level Security and Authentication

Supabase provides built-in Row-Level Security (RLS) for secure data access:

```sql
-- Example RLS policy for tours
ALTER TABLE tours ENABLE ROW LEVEL SECURITY;

CREATE POLICY tour_access_policy ON tours
    USING (agent_id = auth.uid() OR auth.role() = 'admin');
```

## 3. Upstash Redis Implementation

### 3.1 Cache Key Structure

Establish a consistent cache key naming convention:

- `reanna:tour:{tour_id}` - Cache tour data
- `reanna:visits:{tour_id}` - Cache property visits for a tour
- `reanna:next_visit:{tour_id}` - Cache next property visit for a tour
- `reanna:token:{service_name}` - Cache authentication tokens
- `reanna:rate_limit:{service_name}:{endpoint}` - Rate limit tracking
- `reanna:circuit:{service_name}` - Circuit breaker state
- `reanna:metrics:{metric_type}:{timeframe}` - Real-time metrics
- `reanna:dashboard:{component}` - Dashboard data

### 3.2 Caching Strategies

#### 3.2.1 Dashboard Data Caching

```python
# Example implementation
async def get_dashboard_metrics():
    cache_key = "reanna:dashboard:overview"
    
    # Try to get from cache first
    cached_data = await redis.get(cache_key)
    if cached_data:
        return json.loads(cached_data)
    
    # If not in cache, fetch from database
    metrics = await db.fetch_dashboard_metrics()
    
    # Store in cache with 5-minute expiration
    await redis.set(cache_key, json.dumps(metrics), ex=300)
    
    return metrics
```

#### 3.2.2 Circuit Breaker State Management

```python
# Example implementation
async def get_circuit_state(service_name):
    cache_key = f"reanna:circuit:{service_name}"
    
    state = await redis.hgetall(cache_key)
    if not state:
        # Default closed state
        state = {
            "state": "CLOSED",
            "failure_count": 0,
            "last_failure": None,
            "last_success": datetime.utcnow().isoformat()
        }
        await redis.hmset(cache_key, state)
    
    return state

async def record_failure(service_name):
    cache_key = f"reanna:circuit:{service_name}"
    
    # Atomic increment of failure count
    failure_count = await redis.hincrby(cache_key, "failure_count", 1)
    await redis.hset(cache_key, "last_failure", datetime.utcnow().isoformat())
    
    # Record to database for persistence
    await db.insert_circuit_breaker_event(
        service_name=service_name,
        previous_state=await redis.hget(cache_key, "state"),
        new_state="OPEN" if failure_count >= THRESHOLD else await redis.hget(cache_key, "state"),
        failure_count=failure_count
    )
    
    # If threshold reached, open circuit
    if failure_count >= THRESHOLD:
        await redis.hset(cache_key, "state", "OPEN")
        await redis.hset(cache_key, "opened_at", datetime.utcnow().isoformat())
        # Expire after recovery timeout to force retry
        await redis.expire(cache_key, RECOVERY_TIMEOUT)
```

#### 3.2.3 Rate Limit Tracking

```python
# Example implementation
async def check_rate_limit(service_name, endpoint, limit=100, window=3600):
    cache_key = f"reanna:rate_limit:{service_name}:{endpoint}"
    
    # Use Redis sorted set with timestamps as scores
    current_time = time.time()
    expiration_time = current_time - window
    
    # Remove expired entries
    await redis.zremrangebyscore(cache_key, 0, expiration_time)
    
    # Count current entries
    count = await redis.zcard(cache_key)
    
    if count >= limit:
        return False, count, await redis.zrange(cache_key, 0, 0)
    
    # Add new request
    await redis.zadd(cache_key, {str(uuid.uuid4()): current_time})
    # Set expiration on the key itself
    await redis.expire(cache_key, window * 2)
    
    return True, count + 1, None
```

### 3.3 Pub/Sub for Alerts and Notifications

```python
# Example implementation
async def publish_alert(alert_type, entity_id, entity_type, message, severity):
    # Store in database
    alert_id = await db.insert_alert(
        alert_type=alert_type,
        entity_id=entity_id,
        entity_type=entity_type,
        message=message,
        severity=severity
    )
    
    # Publish to Redis channel
    alert_data = {
        "id": alert_id,
        "alert_type": alert_type,
        "entity_id": entity_id,
        "entity_type": entity_type,
        "message": message,
        "severity": severity,
        "timestamp": datetime.utcnow().isoformat()
    }
    
    await redis.publish("reanna:alerts", json.dumps(alert_data))
    return alert_id

# In notification service
async def start_alert_listener():
    pubsub = redis.pubsub()
    await pubsub.subscribe("reanna:alerts")
    
    while True:
        message = await pubsub.get_message(ignore_subscribe_messages=True)
        if message:
            alert_data = json.loads(message["data"])
            await process_alert(alert_data)
        
        await asyncio.sleep(0.01)
```

## 4. Webhook Router Service

### 4.1 Purpose and Benefits

A dedicated webhook router service would provide:

1. **Decoupled Integration**: Separate handling of external events from core business logic
2. **Enhanced Reliability**: Specialized retry and error handling for webhook processing
3. **Scalability**: Independent scaling based on webhook volume
4. **Unified Interface**: Common entry point for all external service webhooks
5. **Event Normalization**: Convert various webhook formats to standardized internal events

### 4.2 Architecture Design

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────────┐
│                 │      │                  │      │                 │
│  External CRMs  │─────►│  Webhook Router  │─────►│  REanna Router  │
│   & Services    │      │     Service      │      │    Services     │
│                 │      │                  │      │                 │
└─────────────────┘      └──────────────────┘      └─────────────────┘
                                  │
                                  │
                          ┌───────▼──────┐
                          │              │
                          │   Redis      │
                          │   Streams    │
                          │              │
                          └──────────────┘
```

### 4.3 Key Components

#### 4.3.1 Webhook Endpoints

```python
# Example implementation
@app.post("/webhooks/{provider}")
async def handle_webhook(provider: str, request: Request):
    # Verify webhook authenticity based on provider
    verify_result = await verify_webhook(provider, request)
    if not verify_result:
        return JSONResponse(status_code=401, content={"error": "Invalid webhook signature"})
    
    # Parse the webhook payload
    payload = await request.json()
    
    # Normalize to standard event format
    event = await normalize_event(provider, payload)
    
    # Add to Redis stream for processing
    await redis.xadd(
        "webhooks:events", 
        {
            "provider": provider,
            "event_type": event["type"],
            "payload": json.dumps(event),
            "received_at": datetime.utcnow().isoformat()
        }
    )
    
    # Acknowledge receipt
    return {"status": "accepted"}
```

#### 4.3.2 Event Consumer

```python
# Example implementation
async def process_webhook_events():
    last_id = "0"
    while True:
        # Read new events from stream
        events = await redis.xread({"webhooks:events": last_id}, count=10, block=5000)
        
        for stream, stream_events in events:
            for event_id, event_data in stream_events:
                try:
                    # Process event
                    await process_event(event_data)
                    
                    # Acknowledge processing
                    await redis.xack("webhooks:events", "webhook-consumer", event_id)
                    
                    # Remove processed event
                    await redis.xdel("webhooks:events", event_id)
                    
                    # Update last processed ID
                    last_id = event_id
                except Exception as e:
                    # Log error and continue
                    logger.error(f"Error processing webhook event {event_id}: {str(e)}")
                    
                    # Move to error stream after too many retries
                    retry_count = await increment_retry_count(event_id)
                    if retry_count > MAX_RETRIES:
                        await redis.xadd("webhooks:errors", {**event_data, "error": str(e)})
                        await redis.xdel("webhooks:events", event_id)
        
        await asyncio.sleep(0.1)
```

#### 4.3.3 Provider-Specific Handlers

```python
# Example implementation
async def normalize_event(provider, payload):
    if provider == "gohighlevel":
        return normalize_ghl_webhook(payload)
    elif provider == "rollout":
        return normalize_rollout_webhook(payload)
    elif provider == "lofty":
        return normalize_lofty_webhook(payload)
    else:
        # Generic normalization
        return {
            "provider": provider,
            "type": payload.get("event_type", "unknown"),
            "data": payload,
            "timestamp": datetime.utcnow().isoformat()
        }
```

### 4.4 Docker Configuration

```dockerfile
# Dockerfile for Webhook Router
FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "webhook_router.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 5. Migration Strategy

### 5.1 Preparation Phase

#### 5.1.1 Database Schema Creation

1. Set up Supabase project
2. Create tables and indexes from schema definitions
3. Configure Row-Level Security and authentication
4. Create database roles and permissions

#### 5.1.2 Application Changes

1. Create database abstraction layer to support both SQLite and Supabase
2. Update database connection code to use environment variables
3. Implement adapter pattern for cache operations
4. Add Upstash Redis client configuration

#### 5.1.3 Testing Environment

1. Set up staging environment with Supabase and Upstash
2. Create test data migration scripts
3. Develop automated tests for database operations
4. Configure CI pipeline for testing

### 5.2 Data Migration Process

#### 5.2.1 Initial Data Migration

```python
# Example implementation
async def migrate_data():
    # Connect to SQLite
    sqlite_conn = sqlite3.connect("reanna_router.db")
    sqlite_cursor = sqlite_conn.cursor()
    
    # Connect to Supabase
    supabase_client = create_supabase_client()
    
    # Migrate tours
    sqlite_cursor.execute("SELECT id, agent_id, start_time, end_time, status, route_data FROM tours")
    tours = sqlite_cursor.fetchall()
    
    for tour in tours:
        id, agent_id, start_time, end_time, status, route_data = tour
        
        # Insert to Supabase
        await supabase_client.table("tours").insert({
            "id": id,
            "agent_id": agent_id,
            "start_time": start_time,
            "end_time": end_time,
            "status": status,
            "route_data": json.loads(route_data) if route_data else None
        }).execute()
    
    # Continue with property_visits, tasks, feedback...
```

#### 5.2.2 Incremental Data Migration

For production systems with continuous operation:

1. Enable write-through caching to both SQLite and Supabase
2. Gradually move read operations to Supabase
3. Verify data consistency between systems
4. Once verified, switch write operations to Supabase only

### 5.3 Cutover Strategy

#### 5.3.1 Read-Only Cutover

1. Put application in read-only mode temporarily
2. Perform final data synchronization
3. Update environment configuration to use Supabase and Upstash
4. Switch application to read-write mode with new database

#### 5.3.2 Blue-Green Deployment

1. Deploy new version pointing to Supabase/Upstash alongside existing version
2. Perform final data synchronization
3. Switch traffic to new version
4. Keep old version running for quick rollback if needed

### 5.4 Rollback Plan

1. Maintain SQLite database structure during initial migration period
2. Create data export scripts from Supabase to SQLite format
3. Test rollback procedure before production cutover
4. Document step-by-step rollback process for emergencies

## 6. Railway Deployment

### 6.1 Project Structure

```
reanna-router/
├── app/
│   ├── api/
│   ├── models/
│   ├── services/
│   ├── utils/
│   └── main.py
├── webhook-router/
│   ├── handlers/
│   ├── utils/
│   └── main.py
├── scripts/
│   ├── migration/
│   └── testing/
├── Dockerfile
├── docker-compose.yml
├── railway.json
└── requirements.txt
```

### 6.2 Docker Configuration

```dockerfile
# Dockerfile for REanna Router
FROM python:3.9-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 6.3 Railway Configuration

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE",
    "dockerfilePath": "./Dockerfile"
  },
  "deploy": {
    "startCommand": "uvicorn app.main:app --host 0.0.0.0 --port $PORT",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  }
}
```

### 6.4 Environment Configuration

Required environment variables:

```
# Database
DATABASE_URL=postgresql://postgres:[PASSWORD]@[HOST]:[PORT]/postgres
SUPABASE_URL=https://[PROJECT_ID].supabase.co
SUPABASE_KEY=[API_KEY]

# Redis
REDIS_URL=redis://[USERNAME]:[PASSWORD]@[HOST]:[PORT]
UPSTASH_REDIS_REST_URL=https://[REGION].[HOST].upstash.io
UPSTASH_REDIS_REST_TOKEN=[TOKEN]

# Application
PORT=8080
ENV=production
LOG_LEVEL=info

# Authentication
JWT_SECRET=[SECRET]
API_KEY=[API_KEY]

# External Services
GOOGLE_MAPS_API_KEY=[API_KEY]
ROLLOUT_CLIENT_ID=[CLIENT_ID]
ROLLOUT_CLIENT_SECRET=[CLIENT_SECRET]
```

## 7. Implementation Timeline

### 7.1 Phase 1: Preparation and Development (2 weeks)

- Set up Supabase and Upstash projects
- Create database schema
- Develop adapter patterns for database and cache
- Update application code for new backend services
- Implement and test data migration scripts

### 7.2 Phase 2: Webhook Router Development (2 weeks)

- Design and implement webhook endpoints
- Create event normalization logic
- Develop Redis Streams consumers
- Test with mock webhooks

### 7.3 Phase 3: Testing and Staging (1 week)

- Deploy to staging environment
- Perform integration testing
- Test data migration with real data
- Measure performance and optimize

### 7.4 Phase 4: Production Deployment (1 week)

- Finalize production environment configuration
- Perform database migration
- Deploy updated application
- Monitor system performance

### 7.5 Phase 5: Validation and Optimization (1 week)

- Verify all functionality works with new infrastructure
- Optimize cache strategies
- Fine-tune database performance
- Document production setup

## 8. Conclusion

This implementation plan provides a comprehensive approach to migrating REanna Router from SQLite to a production-ready database architecture using Supabase and Upstash Redis. The addition of a webhook router service enhances the system's integration capabilities, making it more robust and scalable.

The phased migration strategy ensures minimal disruption to existing operations while enabling a smooth transition to the new infrastructure. By leveraging managed services like Supabase and Upstash, the team can focus on application development rather than infrastructure management.

Once implemented, this architecture will provide a solid foundation for future growth, including enhanced CRM integrations, real-time features, and advanced analytics capabilities.
