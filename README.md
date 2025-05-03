### Nibble

<p align="center">
  <img src="/images/Nibble-logo2.png" alt="Nibble Logo" width="300" height="auto">
</p>

## 📚 Overview

This project implements a full-featured food delivery platform similar to Wolt, using a microservices architecture to ensure scalability, resilience, and maintainability. Each service is containerized using Docker, allowing for easy deployment and scaling.

## 🏗️ Architecture

This project uses a microservices architecture, with the following core services:

- **API Gateway**: Entry point for all API requests
- **User Service**: User authentication and profile management
- **Restaurant Service**: Restaurant and menu management
- **Order Service**: Order processing and cart management
- **Driver Service**: Driver management and delivery tracking
- **Admin Service**: Administrative dashboard and operations
- **Analytics Service**: Real-time analytics and reporting

### 🔧 Technology Stack

- **Backend Framework**: [FastAPI](https://fastapi.tiangolo.com/) - High-performance Python web framework
- **Database**: [PostgreSQL](https://www.postgresql.org/) - Reliable, feature-rich SQL database
- **Caching**: [Redis](https://redis.io/) - In-memory data store for caching and session management
- **Message Broker**: [Apache Kafka](https://kafka.apache.org/) - Event streaming platform for service communication
- **Analytics**: [Apache Pinot](https://pinot.apache.org/) - Real-time distributed OLAP datastore
- **Containerization**: [Docker](https://www.docker.com/) - Container platform for deployment
- **Service Orchestration**: Docker Compose for local development

## 🚀 Getting Started

### Prerequisites

- Docker and Docker Compose
- ~3GB of free RAM (the project requires approximately 2.96GB)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/Darkhan2123/uber-eats-fastapi-clone.git
   cd uber-eats-fastapi-clone
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

3. Access the API documentation:
   - http://localhost:8000/docs - API Gateway

   - http://localhost:8001/docs - User Service endpoints

   - http://localhost:8002/docs - Restaurant Service endpoints

   - http://localhost:8003/docs - Driver Service endpoints

   - http://localhost:8004/docs - Order Service endpoints

   - http://localhost:8005/docs - Admin Service endpoints

   - http://localhost:8006/docs - Dashboard, Analytics Service endpoints

    # For a complete list of available endpoints, see [API_PATHS.md](API_PATHS.md).

## 🔐 Authentication

Most API endpoints require authentication. Include an `Authorization` header with a valid JWT token:

```
Authorization: Bearer your_jwt_token_here
```

You can obtain a token through the `/api/auth/login` endpoint.

## 🎯 Design Decisions & System Capabilities

### Scalability: How does the design handle growth in users or data?

Our system is designed to scale efficiently through:

1. **Microservices Architecture**: Each service can be scaled independently based on demand
2. **Database Sharding**: PostgreSQL can be sharded for horizontal scaling
3. **Caching Strategy**: Redis reduces database load for frequently accessed data
4. **Event-Driven Communication**: Kafka enables asynchronous processing and loose coupling
5. **Stateless Services**: All services are designed to be stateless, enabling horizontal scaling
6. **Read Replicas**: Database read replicas can be added to handle increased query volume
7. **Geographical Distribution**: Services can be deployed closer to users in different regions

For a 1000x growth scenario, we would implement:
- Additional database sharding
- More sophisticated caching strategies
- Expanded Kafka clusters
- CDN integration for static content
- Optimized query patterns and indexes

### Data Protection: How are you protecting personal data?

Personal data protection is implemented through:

1. **JWT-Based Authentication**: Secure user authentication with expiring tokens
2. **Role-Based Access Control**: Restricting access based on user roles
3. **Data Encryption**: Sensitive data is encrypted at rest and in transit
4. **API Rate Limiting**: Prevention of brute force and DoS attacks
5. **Input Validation**: All requests are validated using Pydantic models
6. **Minimal Data Exposure**: API responses only include necessary data
7. **Service Isolation**: Each service only accesses the data it needs
8. **Audit Logging**: All data access and modifications are logged

### Fault Tolerance: Can your system handle failures or downtime gracefully?

The system is designed for resilience:

1. **Service Isolation**: Failures in one service don't cascade to others
2. **Circuit Breakers**: Prevent cascading failures when services are unresponsive
3. **Event Persistence**: Kafka retains messages, allowing services to recover after downtime
4. **Graceful Degradation**: Core functionality continues even if non-critical services are down
5. **Health Checks**: Regular monitoring detects issues early
6. **Automated Recovery**: Docker's restart policies automatically recover failed containers
7. **Database Reliability**: PostgreSQL provides strong consistency and durability
8. **Redundancy**: Critical services can be replicated for high availability

## 👨‍💻 Development

### Project Structure

```
.
├── api-gateway/               # API Gateway service
├── docker-compose.yml         # Docker compose configuration
├── infrastructure/            # Infrastructure configuration
│   ├── kafka/                 # Kafka configuration
│   ├── pinot/                 # Apache Pinot configuration
│   └── postgres/              # PostgreSQL scripts and migrations
└── services/                  # Microservices
    ├── admin/                 # Admin service
    ├── analytics/             # Analytics service
    ├── driver/                # Driver service
    ├── notification/          # Notification service
    ├── order/                 # Order service
    ├── restaurant/            # Restaurant service
    └── user/                  # User service
```
