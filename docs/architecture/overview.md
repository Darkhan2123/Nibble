# Architecture Overview

The Nibble project is built using a microservices architecture to create a scalable, resilient, and maintainable food delivery platform. This document provides a high-level overview of the architectural design.

## Architectural Style

The system is built using a **microservices architecture** with the following characteristics:

- **Service Independence**: Each service is developed, deployed, and scaled independently
- **Domain-Driven Design**: Services are organized around business capabilities
- **API-First Approach**: All services expose and consume well-defined APIs
- **Event-Driven Communication**: Asynchronous event-based communication using Kafka
- **Containerized Deployment**: All services are containerized using Docker

## Core Services

![Architecture Diagram](./diagrams/architecture-overview.png)

The system consists of the following core services:

### 1. API Gateway
Acts as the entry point for all client requests, handling routing, authentication, and request/response transformation.

**Key Responsibilities**:
- Route requests to appropriate microservices
- Handle authentication and JWT token validation
- Response caching with Redis
- Error handling and request logging

### 2. User Service
Manages all user-related functionality including authentication, profile management, and user preferences.

**Key Responsibilities**:
- User registration and authentication
- Profile management
- Address management
- Review submission
- Favorites management

### 3. Restaurant Service
Manages restaurant profiles, menus, and inventory.

**Key Responsibilities**:
- Restaurant profile management
- Menu and category management
- Operating hours management
- Order acceptance and status updates
- Restaurant-side analytics

### 4. Order Service
Handles order creation, processing, and payment.

**Key Responsibilities**:
- Shopping cart management
- Order creation and validation
- Payment processing
- Order status tracking
- Order history

### 5. Driver Service
Manages driver profiles, delivery assignments, and location tracking.

**Key Responsibilities**:
- Driver profile management
- Delivery assignment
- Real-time location tracking
- Delivery status updates
- Driver performance metrics

### 6. Admin Service
Provides administrative capabilities for platform management.

**Key Responsibilities**:
- User management
- Restaurant approval and management
- Driver verification
- Support ticket management
- Promotion and campaign management

### 7. Analytics Service
Provides business intelligence and analytical data processing.

**Key Responsibilities**:
- Order analytics
- Restaurant performance metrics
- Driver performance metrics
- Real-time business dashboards
- Data visualization

### 8. Notification Service
Handles various types of notifications to users.

**Key Responsibilities**:
- Email notifications
- Push notifications
- SMS notifications
- In-app notifications
- Notification preferences

## Technology Stack

The system uses the following core technologies:

- **Backend Framework**: FastAPI (Python)
- **Database**: PostgreSQL with PostGIS for spatial data
- **Caching**: Redis
- **Message Queue**: Apache Kafka with FastStream library
- **Analytics Database**: Apache Pinot (OLAP)
- **Containerization**: Docker and Docker Compose
- **API Documentation**: Swagger UI via FastAPI

## Communication Patterns

The system employs two primary communication patterns:

### 1. Synchronous Communication (REST APIs)
Used for:
- User-facing requests requiring immediate responses
- Simple CRUD operations
- Queries requiring up-to-date data

### 2. Asynchronous Communication (Event-Driven)
Used for:
- Cross-service workflows (e.g., order processing pipeline)
- Notifications and alerts
- Analytics data processing
- Operations that can be processed in the background

## Data Management

The system follows these data management principles:

- **Data Ownership**: Each service owns and manages its own data
- **Database Per Service**: Each service has its dedicated database schema
- **Eventual Consistency**: The system prioritizes availability and partition tolerance over strict consistency
- **CQRS Pattern**: For services with complex read requirements (particularly analytics)

## Security Architecture

The security architecture is built around:

- **JWT-Based Authentication**: JSON Web Tokens for session management
- **Role-Based Access Control**: Different permissions for customers, restaurants, drivers, and admins
- **Service-to-Service Authentication**: For internal communications
- **Data Encryption**: For sensitive information
- **Input Validation**: Using Pydantic schemas

## Next Steps

For more detailed information about specific aspects of the architecture, please refer to:

- [Architecture Decision Records](./decisions/README.md) - for the reasoning behind key architectural decisions
- [System Component Diagrams](./diagrams/README.md) - for visual representations of the system
- [Data Flow Documentation](./data-flows/README.md) - for detailed information about data flows
