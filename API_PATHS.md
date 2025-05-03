# Uber Eats FastAPI Clone API Paths

This document outlines the various API paths available in the Uber Eats FastAPI Clone application.

## Authentication

Authentication is required for most endpoints. You need to include an `Authorization` header with a valid JWT token:

```
Authorization: Bearer your_jwt_token_here
```

## API Gateway

The API Gateway serves as the entry point for all API requests at `http://localhost:8000`.

### Public Endpoints

These endpoints do not require authentication:

- `GET /api/health`: Check system health and service status
- `GET /`: API status information
- `GET /docs`: API documentation (Swagger UI)
- `POST /api/auth/login`: Login endpoint
- `POST /api/auth/register`: Registration endpoint
- `POST /api/auth/refresh`: Token refresh endpoint
- `POST /api/auth/logout`: Logout endpoint

### Admin Service Endpoints

Admin service endpoints require admin authentication:

- `GET /api/admin/dashboard/summary`: Get admin dashboard summary statistics
- `GET /api/admin/dashboard/orders-chart`: Get order chart data
- `GET /api/admin/dashboard/revenue-chart`: Get revenue chart data
- `GET /api/admin/dashboard/top-restaurants`: Get top performing restaurants
- `GET /api/admin/dashboard/recent-activity`: Get recent system activity
- `GET /api/admin/users`: Get users (admin access)
- `GET /api/admin/promotions`: Get all promotions
- `POST /api/admin/promotions`: Create a new promotion
- `GET /api/admin/promotions/{id}`: Get a specific promotion
- `PUT /api/admin/promotions/{id}`: Update a promotion
- `DELETE /api/admin/promotions/{id}`: Delete a promotion
- `GET /api/admin/tickets`: Get all support tickets
- `POST /api/admin/tickets`: Create a new support ticket
- `GET /api/admin/tickets/{id}`: Get a specific support ticket
- `PUT /api/admin/tickets/{id}`: Update a support ticket
- `DELETE /api/admin/tickets/{id}`: Delete a support ticket

### User Service Endpoints

User-related endpoints:

- `GET /api/users/me`: Get current user profile
- `PUT /api/users/me`: Update current user profile
- `GET /api/users/{id}`: Get user by ID
- `PUT /api/users/{id}`: Update user
- `DELETE /api/users/{id}`: Delete user
- `GET /api/users/{id}/addresses`: Get user addresses
- `POST /api/users/{id}/addresses`: Add a new address
- `PUT /api/users/{id}/addresses/{address_id}`: Update an address
- `DELETE /api/users/{id}/addresses/{address_id}`: Delete an address

### Restaurant Service Endpoints

Restaurant-related endpoints:

- `GET /api/restaurants`: Get all restaurants
- `POST /api/restaurants`: Create a new restaurant
- `GET /api/restaurants/{id}`: Get restaurant by ID
- `PUT /api/restaurants/{id}`: Update restaurant
- `DELETE /api/restaurants/{id}`: Delete restaurant
- `GET /api/restaurants/{id}/menu`: Get restaurant menu
- `POST /api/restaurants/{id}/menu`: Add a menu item
- `PUT /api/restaurants/{id}/menu/{item_id}`: Update a menu item
- `DELETE /api/restaurants/{id}/menu/{item_id}`: Delete a menu item
- `GET /api/restaurants/{id}/orders`: Get restaurant orders

### Order Service Endpoints

Order-related endpoints:

- `GET /api/orders`: Get user orders
- `POST /api/orders`: Create a new order
- `GET /api/orders/{id}`: Get order by ID
- `PUT /api/orders/{id}`: Update order status
- `DELETE /api/orders/{id}`: Cancel order
- `GET /api/orders/{id}/payments`: Get order payment information
- `POST /api/orders/{id}/payments`: Process a payment
- `GET /api/cart`: Get user's cart
- `POST /api/cart`: Add item to cart
- `PUT /api/cart/{item_id}`: Update cart item
- `DELETE /api/cart/{item_id}`: Remove cart item

### Driver Service Endpoints

Driver-related endpoints:

- `GET /api/drivers`: Get all drivers
- `POST /api/drivers`: Create a new driver
- `GET /api/drivers/{id}`: Get driver by ID
- `PUT /api/drivers/{id}`: Update driver
- `DELETE /api/drivers/{id}`: Delete driver
- `GET /api/drivers/{id}/deliveries`: Get driver deliveries
- `PUT /api/drivers/{id}/deliveries/{delivery_id}`: Update delivery status

### Analytics Service Endpoints

Analytics-related endpoints:

- `GET /api/analytics/orders`: Get order analytics
- `GET /api/analytics/restaurants`: Get restaurant analytics
- `GET /api/analytics/drivers`: Get driver analytics

## Error Handling

All API endpoints follow standard HTTP status codes:

- `200 OK`: Request successful
- `201 Created`: Resource successfully created
- `400 Bad Request`: Invalid input
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

Error responses include a JSON payload with details:

```json
{
  "detail": "Error message here"
}
```