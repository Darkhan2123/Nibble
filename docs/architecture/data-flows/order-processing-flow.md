# Order Processing Flow

This document details the order processing flow in the Nibble platform, from initial cart creation to order completion.

## Overview

The order processing flow is a core business process that spans multiple services and utilizes both synchronous and asynchronous communication patterns. It handles the entire lifecycle of an order, including cart management, payment processing, restaurant confirmation, driver assignment, delivery tracking, and completion.

## Flow Diagram
https://www.mermaidchart.com/raw/2f824816-f447-49d5-869d-3102d6b6650a?theme=light&version=v0.1&format=svg

## Step-by-Step Process

### 1. Cart Management Phase
1. **Add Item to Cart**:
   - User adds items to their cart through the API Gateway
   - Order Service stores cart items in Redis or PostgreSQL
   - Items are associated with the user ID and have a configurable expiration time

2. **Update Cart**:
   - User can modify quantities or remove items
   - Cart totals are recalculated (subtotal, tax, delivery fee, etc.)

3. **Apply Promotions** (optional):
   - User can apply promo codes
   - Order Service validates the code and applies the discount

### 2. Order Creation Phase
1. **Place Order**:
   - User submits the order with delivery address, payment method, and special instructions
   - API Gateway forwards the request to the Order Service
   - Order Service validates the cart (item availability, restaurant open status, etc.)
   - Order Service creates a new order record with status "pending"
   - Order Service publishes an `order_created` event to Kafka

2. **Payment Processing**:
   - Order Service initiates payment processing
   - If successful, Order Service updates order status to "paid"
   - Order Service publishes a `payment_completed` event
   - If failed, Order Service publishes a `payment_failed` event and the flow terminates

### 3. Restaurant Confirmation Phase
1. **Restaurant Notification**:
   - Restaurant Service consumes the `payment_completed` event
   - Restaurant Service updates its local order record
   - Notification Service sends an alert to the restaurant

2. **Order Acceptance**:
   - Restaurant accepts the order through their interface
   - Restaurant Service updates the order status to "confirmed"
   - Restaurant Service publishes an `order_confirmed` event
   - Restaurant Service estimates preparation time

### 4. Driver Assignment Phase
1. **Driver Selection**:
   - Driver Service consumes the `order_confirmed` event
   - Driver Service runs an assignment algorithm considering:
     - Driver proximity to restaurant
     - Driver ratings
     - Current delivery load
     - Historical performance
   - Driver Service assigns the order to a driver
   - Driver Service publishes a `driver_assigned` event

2. **Driver Notification**:
   - Notification Service consumes the `driver_assigned` event
   - Notification Service sends pickup notification to the driver
   - Notification Service informs the customer about their assigned driver

### 5. Food Preparation and Pickup Phase
1. **Preparation Tracking**:
   - Restaurant updates order status to "preparing"
   - Restaurant Service publishes an `order_preparing` event
   - When food is ready, restaurant updates status to "ready_for_pickup"
   - Restaurant Service publishes an `order_ready` event

2. **Driver Pickup**:
   - Driver arrives at restaurant and collects the order
   - Driver Service updates order status to "picked_up"
   - Driver Service publishes an `order_picked_up` event
   - Notification Service informs the customer their food is on the way

### 6. Delivery Phase
1. **Delivery Tracking**:
   - Driver Service periodically updates driver location
   - Driver Service publishes `driver_location_updated` events
   - Order Service estimates arrival time based on location updates

2. **Delivery Completion**:
   - Driver marks the delivery as completed
   - Driver Service updates the order status to "delivered"
   - Driver Service publishes a `delivery_completed` event
   - Order Service finalizes the order
   - Notification Service sends delivery confirmation to the customer

### 7. Post-Delivery Phase
1. **Review Prompt**:
   - After a configured delay, Notification Service sends a review prompt
   - Customer can rate the food and delivery experience

2. **Analytics Processing**:
   - Throughout the flow, analytics events are captured
   - Order data is processed by Analytics Service for reporting

## Services Involved

| Service | Responsibility in Order Flow |
|---------|------------------------------|
| **API Gateway** | Routes user requests to appropriate services |
| **Order Service** | Manages cart, creates orders, handles payment initiation |
| **Payment Service** | Processes payments and handles payment gateway integration |
| **Restaurant Service** | Handles restaurant-side order management |
| **Driver Service** | Manages driver assignment and delivery tracking |
| **Notification Service** | Sends notifications to all parties |
| **Analytics Service** | Processes order data for business intelligence |

## API Endpoints

### Order Service
- `POST /api/v1/cart` - Add item to cart
- `PUT /api/v1/cart/{item_id}` - Update cart item
- `DELETE /api/v1/cart/{item_id}` - Remove cart item
- `GET /api/v1/cart` - Get cart contents
- `POST /api/v1/orders` - Create order
- `GET /api/v1/orders/{id}` - Get order details
- `GET /api/v1/orders` - List user orders

### Restaurant Service
- `GET /api/v1/restaurants/{id}/orders` - Get restaurant orders
- `PUT /api/v1/restaurants/{id}/orders/{order_id}` - Update order status

### Driver Service
- `GET /api/v1/drivers/{id}/deliveries` - Get assigned deliveries
- `PUT /api/v1/drivers/{id}/deliveries/{delivery_id}` - Update delivery status

## Kafka Events

| Event Type | Producer | Consumers | Purpose |
|------------|----------|-----------|---------|
| `order_created` | Order Service | Analytics Service | Record new order creation |
| `payment_completed` | Order Service | Restaurant Service, Notification Service | Signal successful payment |
| `payment_failed` | Order Service | Notification Service | Signal failed payment |
| `order_confirmed` | Restaurant Service | Driver Service, Notification Service | Signal restaurant acceptance |
| `driver_assigned` | Driver Service | Order Service, Notification Service | Signal driver assignment |
| `order_preparing` | Restaurant Service | Order Service, Notification Service | Update preparation status |
| `order_ready` | Restaurant Service | Driver Service, Notification Service | Signal order ready for pickup |
| `order_picked_up` | Driver Service | Order Service, Notification Service | Signal driver has picked up order |
| `driver_location_updated` | Driver Service | Order Service | Update delivery location |
| `delivery_completed` | Driver Service | Order Service, Notification Service | Signal completed delivery |
| `order_completed` | Order Service | Analytics Service, Notification Service | Signal completed order |

## Database Interactions

### Order Service Database
- Cart items stored in Redis (temporary) or PostgreSQL (persistent)
- Order details stored in PostgreSQL
- Order item details stored in PostgreSQL
- Order status history stored in PostgreSQL

### Restaurant Service Database
- Restaurant-side order data stored in PostgreSQL

### Driver Service Database
- Delivery assignments stored in PostgreSQL
- Delivery status history stored in PostgreSQL
- Driver location history stored in PostgreSQL

## Failure Scenarios and Recovery

### 1. Payment Processing Failure
- **Scenario**: Payment gateway returns error or times out
- **Handling**:
  - Order Service marks order as payment_failed
  - Order Service publishes payment_failed event
  - User is notified and prompted to try again
  - Cart items are preserved for retry

### 2. Restaurant Rejection
- **Scenario**: Restaurant rejects the order or fails to confirm within timeout
- **Handling**:
  - Restaurant Service marks order as rejected
  - Restaurant Service publishes order_rejected event
  - Customer is notified with explanation
  - Order Service initiates refund process

### 3. No Available Drivers
- **Scenario**: No drivers available in the area
- **Handling**:
  - Driver Service sets a timeout to retry assignment
  - After multiple attempts, escalates to admin
  - If persistent, customer is notified of delivery delay

### 4. Driver Cancellation
- **Scenario**: Driver cancels or doesn't pick up
- **Handling**:
  - Driver Service marks the assignment as cancelled
  - Driver Service publishes driver_cancelled event
  - Driver Service attempts to find new driver
  - Customer is notified of the reassignment

### 5. Lost Connection with Driver
- **Scenario**: Driver app stops sending location updates
- **Handling**:
  - Driver Service detects missing heartbeats
  - After timeout, order is flagged for investigation
  - Support may contact driver via phone
  - Customer is notified of potential delay

### 6. Kafka Outage
- **Scenario**: Kafka becomes unavailable
- **Handling**:
  - Services implement retry logic with exponential backoff
  - Critical updates use direct API calls as fallback
  - Events are queued locally when possible
  - System eventually recovers when Kafka is restored

## Performance Considerations

1. **Cart Data Storage**:
   - Active carts stored in Redis for fast access
   - Carts have TTL (time-to-live) to prevent stale data accumulation

2. **Order Query Optimization**:
   - Indexes on user_id, restaurant_id, driver_id, and status
   - Pagination implemented for order history endpoints

3. **Event Processing**:
   - Non-critical events processed asynchronously
   - Critical status updates have higher priority
   - Batching used for analytics events

4. **Location Updates**:
   - Throttling applied to prevent excessive location events
   - Spatial indexing used for efficient proximity queries

## Security Considerations

1. **Payment Information**:
   - Payment details never stored directly in our database
   - Integration with payment processor handles sensitive data
   - Tokenization used for recurring payments

2. **Personal Information**:
   - Customer addresses encrypted at rest
   - Driver information access restricted to authorized personnel
   - Delivery instructions filtered for sensitive content

3. **Authentication**:
   - All API calls require valid JWT tokens
   - Different permission levels for customers, restaurants, and drivers

## Further Reading

- [Payment Processing Flow](./payment-flow.md)
- [Driver Assignment Algorithm](../algorithms/driver-assignment.md)
- [Notification Delivery Patterns](./notification-flow.md)
