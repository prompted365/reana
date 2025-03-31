# REanna Router Error Handling and Alert System Knowledge Graph

This document focuses specifically on the error handling, circuit breaking, and alerting subsystems of the REanna Router application. It maps out how errors propagate through the system and how alerts are generated and processed.

## 1. Error Propagation Flow

The error handling system follows this pattern when an external API call fails:

```
┌────────────────────┐
│ External API Call  │
│ (e.g., Rollout API)│
└──────────┬─────────┘
           │
           │ Fails
           ▼
┌────────────────────┐
│ RolloutClient      │
│ Raises Exception   │
└──────────┬─────────┘
           │
           │ Catches & Classifies
           ▼
┌────────────────────┐     ┌────────────────────┐
│ Error Type         │────►│ CircuitBreaker     │
│ Classification     │     │ State Update       │
└──────────┬─────────┘     └────────┬───────────┘
           │                        │
           │                        │
           ▼                        ▼
┌────────────────────┐     ┌────────────────────┐
│ NotificationService│     │ CircuitBreaker     │
│ Error Handling     │     │ Open Event         │
└──────────┬─────────┘     └────────┬───────────┘
           │                        │
           │                        │
           ▼                        ▼
┌────────────────────┐     ┌────────────────────┐
│ Failed Operation   │────►│ AlertManager       │
│ Registration       │     │ record_operation_  │
└────────────────────┘     │ failure            │
                           └────────┬───────────┘
                                    │
                                    │ If threshold exceeded
                                    ▼
                           ┌────────────────────┐
                           │ AlertEvent         │
                           │ Generation         │
                           └────────┬───────────┘
                                    │
                                    │
                            ┌───────┴───────┐
                            │               │
                    ┌───────▼─────┐  ┌──────▼───────┐
                    │ Notification│  │ Failed       │
                    │ Delivery    │  │ Operations   │
                    │ Channels    │  │ Display      │
                    └─────────────┘  └──────────────┘
```

## 2. Error Types and Classification

The system classifies errors into several types that determine how they are handled:

```
┌──────────────────────────────────────────────────────┐
│               RolloutError (Base Class)              │
└──────┬───────────────┬────────────────┬──────────────┘
       │               │                │
┌──────▼──────┐ ┌──────▼────────┐ ┌─────▼──────────┐
│ RolloutRate │ │ RolloutServer │ │ RolloutCircuit │
│ LimitError  │ │ Error         │ │ OpenError      │
└──────┬──────┘ └──────┬────────┘ └─────┬──────────┘
       │               │                │
       │               │                │
       ▼               ▼                ▼
┌─────────────┐ ┌──────────────┐ ┌──────────────────┐
│ Retry with  │ │ Retry with   │ │ No retry until   │
│ exponential │ │ fixed delay  │ │ circuit closes   │
│ backoff     │ │              │ │                  │
└─────────────┘ └──────────────┘ └──────────────────┘
```

### Error Response Strategy:

| Error Type | Alert Level | Alert Type | Retry Strategy | Circuit Breaker Impact |
|------------|-------------|------------|----------------|------------------------|
| RateLimit  | WARNING     | RATE_LIMIT_CRITICAL | Exponential backoff | Increment failure count |
| ServerError| ERROR       | INTEGRATION_ERROR   | Fixed delay        | Increment failure count |
| CircuitOpen| ERROR       | CIRCUIT_BREAKER_OPEN| No retry           | Already open           |
| AuthFailure| CRITICAL    | AUTH_FAILURE        | No retry           | Increment failure count |
| Generic    | ERROR       | REPEATED_SYNC_FAILURE| Based on count    | Increment failure count |

## 3. Circuit Breaker Pattern Implementation

The application implements the Circuit Breaker pattern to prevent cascading failures:

```
┌───────────────────────────────────────────────────────────┐
│                    CircuitBreaker Class                   │
└───────────────────────────┬───────────────────────────────┘
                            │
        ┌──────────────────┬┴───────────────────┐
        │                  │                    │
┌───────▼─────────┐ ┌──────▼──────────┐ ┌───────▼────────┐
│  CLOSED State   │ │  OPEN State     │ │  HALF_OPEN     │
│ (Normal Ops)    │ │(Fail Fast)      │ │  State         │
└───────┬─────────┘ └──────┬──────────┘ └───────┬────────┘
        │                  │                    │
        │   failures > N   │   timeout elapsed  │   success
        └─────►┌───────────┘◄─────┐             └────────┐
               │                  │                      │
               ▼                  │                      │
     ┌───────────────────┐        │                      │
     │  Notify Alert     │        │                      │
     │  Manager          │        │                      │
     └──────────────┬────┘        │                      │
                    │             │                      │
                    └─────────────┘                      │
                          ▲                              │
                          │                              │
                          └──────────────────────────────┘
                                     failure
```

### States Explanation:

* **CLOSED**: Normal operation, calls pass through but failures are counted
* **OPEN**: Circuit is tripped, calls fail fast without reaching the service
* **HALF_OPEN**: Testing if service is recovered; limited calls allowed

## 4. Alert System Components

The alert system consists of several interconnected components:

```
┌────────────────────────────────────────────────────────────┐
│                       AlertManager                         │
└───────────┬────────────────────┬───────────────────────┬───┘
            │                    │                       │
    ┌───────▼─────────┐  ┌───────▼────────┐    ┌────────▼────────┐
    │  Failure        │  │ Threshold      │    │ Notification    │
    │  Tracking       │  │ Checking       │    │ Delivery        │
    └───────┬─────────┘  └───────┬────────┘    └────────┬────────┘
            │                    │                      │
            │                    │                      │
    ┌───────▼─────────┐  ┌───────▼────────┐    ┌────────▼────────┐
    │ _failure_counts │  │ AlertConfig    │    │ AlertMethod     │
    │ Dict per entity │  │ Per alert type │    │ Implementations │
    └─────────────────┘  └────────────────┘    └─────────────────┘
```

### AlertManager Key Components:

1. **Failure Tracking**:
   - Maintains counters of failures by entity and operation type
   - Timestamps failures to calculate rates within time windows
   - Implements cooldown to prevent alert flooding

2. **Threshold Checking**:
   - Configurable thresholds per alert type
   - Time window settings for pattern detection
   - Detects when failures exceed acceptable limits

3. **Notification Delivery**:
   - Multiple channels: LOG, EMAIL, WEBHOOK, SLACK
   - Formatters for each delivery method
   - Configuration for recipients

## 5. Alert Event Flow

When an alert is triggered, it follows this path:

```
┌────────────────────┐
│ AlertManager       │
│ record_operation_  │
│ failure            │
└──────────┬─────────┘
           │
           │ Threshold exceeded
           ▼
┌────────────────────┐
│ _generate_and_send_│
│ alert              │
└──────────┬─────────┘
           │
           │ Create event
           ▼
┌────────────────────┐
│ AlertEvent Object  │
│ Creation           │
└──────────┬─────────┘
           │
           │ Route to methods
           ▼
┌────────────────────┐
│ For each configured│
│ alert method       │
└──────────┬─────────┘
           │
           │
┌──────────┼─────────────────────────────┐
│          │                             │
▼          ▼          ▼          ▼       ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌───────────┐
│_send_  │ │_send_  │ │_send_  │ │_send_     │
│log_    │ │email_  │ │webhook_│ │slack_     │
│alert   │ │alert   │ │alert   │ │alert      │
└────────┘ └────────┘ └────────┘ └───────────┘
```

## 6. Dashboard Integration with Alerts

The dashboard provides visibility into the alert system:

```
┌────────────────────────────────────────────────────────────┐
│                     Dashboard UI                           │
└───────────┬──────────────────────────────────┬─────────────┘
            │                                  │
    ┌───────▼─────────┐              ┌─────────▼───────┐
    │ Alerts Section  │              │ Monitoring      │
    │                 │              │ Section         │
    └───────┬─────────┘              └─────────────────┘
            │
            │
    ┌───────▼─────────┐  ┌────────────────────┐
    │ Recent Alerts   │  │ Alert              │
    │ Table           │  │ Configuration      │
    └─────────────────┘  └────────────────────┘

         ┌───────────────────────────────┐
         │        API Endpoints          │
         └───────────────┬───────────────┘
                         │
         ┌───────────────┴───────────────┐
         │                               │
┌────────▼──────────┐      ┌─────────────▼─────────┐
│/api/monitoring/   │      │/api/monitoring/       │
│alerts             │      │alert-configs          │
└───────────────────┘      └───────────────────────┘
```

## 7. Complete Error Handling Flow Example

Here's an example of a complete error handling flow through the system:

1. **API Call Fails**:
   ```
   RolloutClient attempts to call external API
   External API returns rate limit error (429)
   RolloutRateLimitError is thrown
   ```

2. **Error Handling**:
   ```
   NotificationService catches RolloutRateLimitError
   Creates FailedOperation record with details
   Increments circuit breaker failure counter
   Registers failure with alert_manager
   ```

3. **Alert Processing**:
   ```
   AlertManager checks if entity has exceeded threshold
   Creates AlertEvent for RATE_LIMIT_CRITICAL
   Delivers notification through configured channels
   Implements cooldown to prevent flooding
   ```

4. **UI Display**:
   ```
   Failed operation appears in dashboard
   Alert appears in alerts section
   System health indicator shows degraded status
   Options for manual retry are provided
   ```

This knowledge graph provides a comprehensive view of the error handling architecture in REanna Router, showing how errors propagate through the system, how alert thresholds are evaluated, and how notifications are delivered.