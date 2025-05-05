# Architecture Decision Records (ADRs)

This directory contains Architecture Decision Records (ADRs) documenting the significant architectural decisions made during the development of the Uber Eats FastAPI Clone.

## What is an ADR?

An Architecture Decision Record (ADR) is a document that captures an important architectural decision, including the context, the decision itself, its consequences, and the status of the decision.

## Why ADRs?

ADRs help the team:
- Understand why certain decisions were made
- Revisit decisions when requirements or constraints change
- Onboard new team members effectively
- Track the evolution of the system architecture

## ADR Format

Each ADR follows this format:

```markdown
# ADR-NNN: Title

## Status

[Proposed | Accepted | Deprecated | Superseded]

## Context

[Description of the problem and context]

## Decision

[Description of the decision made]

## Consequences

[Description of the consequences of the decision]

## Alternatives Considered

[Description of alternatives that were considered]

## List of ADRs

1. [ADR-001: Microservices Architecture](./adr-001-microservices-architecture.md)
2. [ADR-002: Event-Driven Communication](./adr-002-event-driven-communication.md)
3. [ADR-003: API Gateway Pattern](./adr-003-api-gateway-pattern.md)
4. [ADR-004: Database Per Service](./adr-004-database-per-service.md)
5. [ADR-005: Authentication with JWT](./adr-005-authentication-with-jwt.md)
6. [ADR-006: Using FastAPI Framework](./adr-006-using-fastapi-framework.md)
7. [ADR-007: Apache Kafka for Messaging](./adr-007-apache-kafka-for-messaging.md)
8. [ADR-008: Apache Pinot for Analytics](./adr-008-apache-pinot-for-analytics.md)
9. [ADR-009: Container Orchestration with Docker Compose](./adr-009-container-orchestration.md)
10. [ADR-010: Redis for Caching and Rate Limiting](./adr-010-redis-for-caching.md)
