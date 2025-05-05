# Data Flow Documentation

This directory contains documentation of the key data flows in the Nibble platform. Understanding these flows is essential for developers to grasp how data moves through the system and how different services interact.

## Purpose

This documentation aims to:
- Provide clear, detailed explanations of how data flows through the system
- Illustrate the interactions between different services
- Document the events and API calls used for data exchange
- Help new developers understand system behavior

## Core Data Flows

1. [Order Processing Flow](./order-processing-flow.md)
2. [User Registration and Authentication Flow](./authentication-flow.md)
3. [Restaurant Onboarding Flow](./restaurant-onboarding-flow.md)
4. [Driver Assignment and Delivery Flow](./delivery-flow.md)
5. [Payment Processing Flow](./payment-flow.md)
6. [Review and Rating Flow](./review-flow.md)
7. [Analytics Data Collection Flow](./analytics-flow.md)
8. [Support Ticket Management Flow](./support-ticket-flow.md)

## Understanding the Documentation

Each data flow document includes:

1. **Overview**: A high-level description of the flow
2. **Flow Diagram**: A visual representation of the data flow
3. **Step-by-Step Process**: Detailed explanation of each step in the flow
4. **Services Involved**: List of services participating in the flow
5. **API Endpoints**: Relevant API endpoints used in the flow
6. **Events**: Kafka events published and consumed during the flow
7. **Database Interactions**: How and when data is persisted
8. **Failure Scenarios**: Common failure cases and how they're handled

## Example: Order Processing Flow

![Order Flow Example](./diagrams/order-flow-simplified.png)

The Order Processing Flow is one of the most complex flows in the system, involving multiple services and both synchronous and asynchronous communication patterns. The full documentation includes details on:

- How orders are created and validated
- Payment processing sequence
- Restaurant notification and acceptance process
- Driver assignment algorithm
- Delivery tracking
- Order status updates
- Analytics event generation