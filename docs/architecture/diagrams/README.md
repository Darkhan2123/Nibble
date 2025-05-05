# System Component Diagrams

This directory contains architectural diagrams that visualize different aspects of the Nibble platform. These diagrams help developers and stakeholders understand the system's structure, components, interactions, and data flows.

## How to Use These Diagrams

- **New Team Members**: Start with the Architecture Overview diagram to understand the big picture, then explore specific service diagrams relevant to your work.
- **Developers**: Reference the detailed service diagrams and data flow diagrams when implementing or modifying features.
- **Technical Leads**: Use these diagrams in architectural discussions and when planning system changes.
- **Product Managers**: The high-level diagrams provide context for feature discussions and planning.

## Diagram Types

### 1. System Architecture Diagrams

- [Architecture Overview](./architecture-overview.png) - High-level view of the entire system
- [Microservices Map](./microservices-map.png) - Visualization of all microservices and their relationships
- [Technology Stack Diagram](./technology-stack.png) - Overview of technologies used in different system layers

### 2. Service-Specific Diagrams

- [User Service Architecture](./user-service-architecture.png)
- [Restaurant Service Architecture](./restaurant-service-architecture.png)
- [Order Service Architecture](./order-service-architecture.png)
- [Driver Service Architecture](./driver-service-architecture.png)
- [Admin Service Architecture](./admin-service-architecture.png)
- [Analytics Service Architecture](./analytics-service-architecture.png)
- [Notification Service Architecture](./notification-service-architecture.png)

### 3. Data Flow Diagrams

- [Order Processing Flow](./order-flow.png)
- [Payment Processing Flow](./payment-flow.png)
- [User Registration Flow](./user-registration-flow.png)
- [Authentication Flow](./authentication-flow.png)
- [Driver Assignment Flow](./driver-assignment-flow.png)
- [Analytics Data Flow](./analytics-flow.png)

### 4. Database Schema Diagrams

- [User Schema](./user-schema.png)
- [Restaurant Schema](./restaurant-schema.png)
- [Order Schema](./order-schema.png)
- [Driver Schema](./driver-schema.png)
- [Admin Schema](./admin-schema.png)

### 5. Deployment Diagrams

- [Development Environment](./dev-deployment.png)
- [Production Environment](./prod-deployment.png)
- [Container Architecture](./container-architecture.png)

### 6. Security Diagrams

- [Authentication Architecture](./authentication-architecture.png)
- [Authorization Flow](./authorization-flow.png)
- [Data Protection Model](./data-protection.png)

## Diagram Standards

All diagrams follow these standards for consistency:

1. **Color Coding**:
   - Blue: User-facing components
   - Green: Internal processing components
   - Yellow: Data storage
   - Red: Security components
   - Purple: External integrations
   - Gray: Infrastructure components

2. **Notation**:
   - Boxes represent services, components, or entities
   - Solid lines represent synchronous communication
   - Dashed lines represent asynchronous communication
   - Database symbols represent data stores
   - Clouds represent external services

3. **Tools**:
   - Diagrams are created using draw.io/diagrams.net
   - Source files (.drawio) are stored alongside PNG exports
   - Mermaid diagrams are used for data flow documentation

## Maintaining These Diagrams

When making significant architectural changes:

1. Update the relevant diagrams to reflect the new structure
2. Store both the source file and the exported image
3. Document the changes in a commit message
4. Consider adding new diagrams for new components or flows

## Example: Architecture Overview

![Architecture Overview](./architecture-overview.png)

*The architecture overview diagram shows the high-level structure of the Nibble platform, including the core microservices, database systems, message broker, and external integrations.*

## Example: Order Processing Flow

![Order Processing Flow](./order-flow.png)

*The order processing flow diagram illustrates the step-by-step process of an order moving through the system, from cart creation to delivery completion.*

## Further Reading

- [C4 Model for Software Architecture](https://c4model.com/)
- [Diagramming Microservices](https://microservices.io/patterns/index.html)
- [UML Diagram Types Guide](https://www.visual-paradigm.com/guide/uml-unified-modeling-language/what-is-uml/)