# ADR-002: Event-Driven Communication

## Status

Accepted

## Context

In our microservices architecture for the Nibble platform, we need an effective strategy for inter-service communication. Services need to share information and coordinate actions while remaining loosely coupled. We need to decide between:

1. Synchronous communication (direct API calls)
2. Asynchronous event-driven communication
3. A hybrid approach

Key considerations include:
- Service independence and loose coupling
- System resilience and fault tolerance
- Performance and scalability
- Consistency requirements
- Development complexity

## Decision

We have decided to implement a **hybrid communication model** with an emphasis on **event-driven communication using Apache Kafka** for most inter-service interactions.

Specifically:

1. **Synchronous Communication (REST API calls)** will be used for:
   - User-facing requests requiring immediate responses
   - Queries that need up-to-date information
   - Simple CRUD operations within a bounded context

2. **Asynchronous Event-Driven Communication** will be used for:
   - Cross-service business processes (e.g., order lifecycle)
   - Notifications and alerts
   - Data replication between services
   - Analytics and reporting
   - Operations that can tolerate eventual consistency

3. **Apache Kafka** will serve as our event streaming platform with:
   - Clear event schema definitions
   - Event versioning strategy
   - The FastStream library for Kafka integration with Python

4. **Event Types and Topics** will be organized by domain:
   - `order-events`: Order creation, updates, cancellations
   - `payment-events`: Payment processing, refunds
   - `restaurant-events`: Menu updates, availability changes
   - `driver-events`: Location updates, delivery status changes
   - `notification-events`: Various notification triggers
   - `analytics-events`: Events specifically for analytics purposes

## Consequences

### Positive

- **Loose Coupling**: Services can evolve independently with minimal coordination as long as event contracts are maintained.
- **Improved Resilience**: Services can continue operating even when dependent services are temporarily unavailable.
- **Enhanced Scalability**: Asynchronous processing allows better handling of traffic spikes through buffering.
- **Temporal Decoupling**: Producer and consumer services don't need to be available simultaneously.
- **Natural Audit Trail**: Events provide a historical record of all system changes.
- **Simplified Integration**: New services can consume relevant events without modifying existing services.
- **Better Performance**: Non-critical operations can be processed asynchronously, improving response times.

### Negative

- **Eventual Consistency**: The system will sometimes be in an inconsistent state between event publication and processing.
- **Increased Complexity**: Event-driven systems are more complex to develop, test, and debug.
- **Message Delivery Challenges**: We need to handle issues like duplicate messages, out-of-order processing, and failed deliveries.
- **Schema Evolution**: Changing event schemas requires careful planning to maintain backward compatibility.
- **Operational Overhead**: Running and maintaining Kafka adds operational complexity.
- **Learning Curve**: The team needs to develop expertise in event-driven architecture patterns.

## Mitigation Strategies

To address the negative consequences:

1. **Event Versioning**: Implement a clear event versioning strategy to manage schema evolution.
2. **Consumer-Driven Contracts**: Establish testing mechanisms to ensure consumers can process producer events.
3. **Idempotent Consumers**: Design event consumers to handle duplicate events gracefully.
4. **Dead Letter Queues**: Set up dead letter topics for events that fail processing.
5. **Monitoring and Alerting**: Implement comprehensive monitoring for Kafka and event processing.
6. **Clear Documentation**: Document event schemas, producers, and consumers for each event type.
7. **Local Development Tools**: Create tools to simplify local development with Kafka.
8. **Event Sourcing Patterns**: Use event sourcing patterns where appropriate to reconstruct state.

## Implementation Details

Our implementation uses:

- **FastStream Library**: For simplified Kafka integration with FastAPI
- **Avro or JSON Schema**: For event schema definition and validation
- **Event Metadata**: Standard metadata fields included in all events:
  - `event_id`: Unique identifier for the event
  - `event_type`: Specific event type
  - `event_version`: Schema version
  - `event_time`: When the event occurred
  - `source_service`: Which service produced the event
  - `correlation_id`: For tracking related events
- **Local Kafka Setup**: Docker Compose configuration for local development

## Alternatives Considered

### Pure REST API Communication

**Advantages**:
- Simpler to implement and understand
- Immediate consistency
- Easier to debug and trace

**Disadvantages**:
- Tight coupling between services
- Reduced resilience (if a service is down, dependent operations fail)
- Synchronous blocking calls reduce performance
- More complex error handling
- Harder to scale for high-throughput scenarios

### Message Queue (RabbitMQ)

**Advantages**:
- Better suited for task distribution
- Lower resource requirements than Kafka
- More mature Python ecosystem

**Disadvantages**:
- Less suitable for event streaming and replay
- Lower throughput than Kafka
- Less scalable for our projected growth
- Limited historical data retention

### Pure Event-Driven

**Advantages**:
- Maximum loose coupling
- Highest potential scalability
- Best fault tolerance

**Disadvantages**:
- Very complex to implement consistently
- Challenging for queries and request-response patterns
- Steeper learning curve
- May be over-engineered for simple operations

## References

- [Martin Fowler on Event-Driven Architecture](https://martinfowler.com/articles/201701-event-driven.html)
- [Confluent Kafka Documentation](https://docs.confluent.io/)
- [FastStream Documentation](https://faststream.airt.ai/latest/)
- [Event-Driven Microservices Architecture by Chris Richardson](https://microservices.io/patterns/data/event-driven-architecture.html)
- [Building Event-Driven Microservices by Adam Bellemare](https://www.oreilly.com/library/view/building-event-driven-microservices/9781492057888/)