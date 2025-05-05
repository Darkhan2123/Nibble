# ADR-003: API Gateway Pattern

## Status

Accepted

## Context

In our microservices architecture for the Nibble platform, we need an effective strategy for client-to-service communication. With multiple client applications (web, mobile) needing to access multiple backend services, we must determine how clients should communicate with the services.

Key considerations include:
- Simplifying the client-side communication
- Handling cross-cutting concerns consistently
- Managing authentication and authorization
- Optimizing network communication
- Providing a unified API experience
- Supporting different client types

We considered several approaches:
1. Direct client-to-microservice communication
2. API Gateway pattern
3. Backend for Frontend (BFF) pattern

## Decision

We have decided to implement an **API Gateway pattern** using FastAPI as the gateway technology.

Specifically:

1. **Centralized Entry Point**:
   - All client requests will go through a single API Gateway
   - The gateway will route requests to appropriate microservices
   - Responses will be returned through the gateway

2. **Key Responsibilities**:
   - Authentication and authorization
   - Request routing
   - Response transformation
   - Protocol translation (if needed)
   - Request/response logging
   - Rate limiting
   - Caching (using Redis)
   - Error handling

3. **Implementation Details**:
   - FastAPI-based API Gateway
   - JWT token validation at the gateway level
   - Redis for token caching and rate limiting
   - Service discovery through configuration
   - Timeout and retry policies for service communication

4. **Service Communication**:
   - The gateway communicates with microservices using HTTP/REST
   - Internal service URLs are not exposed to clients
   - Gateway adds context headers (user ID, roles) to requests

## Consequences

### Positive

- **Simplified Client Integration**: Clients interact with a single endpoint rather than multiple service endpoints.
- **Unified Authentication**: Authentication happens once at the gateway, simplifying client code and ensuring consistent security.
- **Cross-Cutting Concerns**: Features like logging, rate limiting, and monitoring can be implemented once at the gateway level.
- **Abstraction of Services**: Clients are decoupled from the internal service structure, making backend changes less disruptive.
- **Reduced Chattiness**: The gateway can aggregate data from multiple services, reducing the number of client-server round trips.
- **Consistent Error Handling**: Providing unified error responses across all services.
- **Traffic Control**: Ability to throttle or prioritize different types of requests.

### Negative

- **Single Point of Failure**: The API Gateway becomes a critical component that, if it fails, affects all client-service communication.
- **Potential Performance Bottleneck**: All requests passing through the gateway can create a bottleneck.
- **Additional Network Hop**: Every request includes an extra network hop, adding latency.
- **Gateway Complexity**: The gateway needs to handle the nuances of all services, potentially becoming complex over time.
- **Deployment Coupling**: API changes might require coordinated deployment of both services and the gateway.
- **Development Overhead**: Teams need to coordinate API changes with the gateway team or maintain gateway configuration.

## Mitigation Strategies

To address the negative consequences:

1. **High Availability**: Implement the gateway with redundancy and automatic failover.
2. **Performance Optimization**: 
   - Efficient request routing
   - Response caching with Redis
   - Connection pooling for backend services
   - Asynchronous processing using FastAPI's async capabilities
3. **Circuit Breaking**: Implement circuit breakers to prevent cascading failures.
4. **Modular Design**: Design the gateway with clear separation of concerns for long-term maintainability.
5. **Automated Testing**: Comprehensive testing of gateway routing, authentication, and error handling.
6. **Monitoring and Alerting**: Detailed monitoring of gateway performance and health.
7. **Versioned APIs**: Support API versioning to manage changes without breaking clients.

## Implementation Details

### Gateway Architecture

```
+-------------------+     +----------------+
|                   |     |                |
|  Client           |     |  API Gateway   |
|  (Web/Mobile)     +---->+  (FastAPI)     |
|                   |     |                |
+-------------------+     +--------+-------+
                                   |
                                   |
          +------------------------+------------------------+
          |                        |                        |
          v                        v                        v
+------------------+    +-------------------+    +-------------------+
|                  |    |                   |    |                   |
| User Service     |    | Restaurant Service|    | Order Service     |
|                  |    |                   |    |                   |
+------------------+    +-------------------+    +-------------------+
```

### Authentication Flow

1. Client sends credentials to `/api/auth/login` endpoint
2. API Gateway forwards to User Service
3. User Service validates credentials and generates JWT
4. API Gateway caches token in Redis with user context
5. Subsequent requests include JWT in Authorization header
6. API Gateway validates token and adds user context to internal requests

### Request Routing

The API Gateway routes requests based on URL patterns:

```
/api/users/*          → User Service
/api/restaurants/*    → Restaurant Service
/api/orders/*         → Order Service
/api/drivers/*        → Driver Service
/api/admin/*          → Admin Service
/api/analytics/*      → Analytics Service
```

### Error Handling

The API Gateway standardizes error responses across all services:

```json
{
  "detail": "Error message",
  "code": "ERROR_CODE",
  "status": 400
}
```

## Alternatives Considered

### Direct Client-to-Microservice Communication

**Advantages**:
- No single point of failure
- No additional network hop
- Simpler backend architecture

**Disadvantages**:
- Complex client implementation
- Duplication of cross-cutting concerns
- Tight coupling between clients and service internals
- Difficult to maintain consistency across service interactions

### Backend for Frontend (BFF) Pattern

**Advantages**:
- Optimized for specific client types (web, mobile, etc.)
- Better-tailored responses for each client
- Can be more performant for specific clients

**Disadvantages**:
- Duplication of gateway functionality
- More components to maintain
- Potential inconsistencies between BFFs
- Higher development and operational overhead

## References

- [Pattern: API Gateway / Backends for Frontends](https://microservices.io/patterns/apigateway.html)
- [Building Microservices by Sam Newman](https://samnewman.io/books/building_microservices/) - Chapter 5
- [API Gateway Pattern](https://docs.microsoft.com/en-us/azure/architecture/microservices/design/gateway)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Kong API Gateway](https://konghq.com/kong/)