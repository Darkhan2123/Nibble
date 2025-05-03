# User Service

## Overview

The user service handles all user-related functionality in the Nibble application, including:

- User registration and authentication
- User profile management
- Address management with geocoding
- Integration with Yandex Maps for route planning and delivery time estimation
- Restaurant discovery
- Order management and payment processing
- Real-time order tracking

## Features

### Authentication

- User registration with different user types (customer, restaurant, driver)
- Login with email or phone number
- JWT-based authentication with access and refresh tokens
- Role-based authorization

### Address Management

- CRUD operations for user addresses
- Geocoding of addresses to get coordinates
- Validation of address data
- Default address support

### Profile Management

- User profile information
- Customer-specific preferences
- Notification settings

### Restaurant Discovery

- Search for restaurants by location, cuisine, price range
- View restaurant menus
- Get restaurant details

### Order Management

- Create orders with items and customizations
- Process payments (mock implementation)
- Track order status
- View order history
- Cancel orders

### Maps and Delivery Tracking

- Calculate routes between restaurants and delivery addresses
- Estimate delivery times with traffic considerations
- Show maps with delivery routes
- Real-time order tracking

## API Endpoints

### Authentication

- `POST /v1/auth/register` - Register a new customer user
- `POST /v1/auth/register/restaurant` - Register a new restaurant user
- `POST /v1/auth/register/driver` - Register a new driver user
- `POST /v1/auth/login` - Login and get tokens
- `POST /v1/auth/refresh` - Refresh access token
- `POST /v1/auth/logout` - Logout and invalidate token
- `GET /v1/auth/me` - Get current user info

### Address Management

- `GET /v1/addresses` - List all addresses for the current user
- `POST /v1/addresses` - Create a new address
- `GET /v1/addresses/{address_id}` - Get address details
- `PUT /v1/addresses/{address_id}` - Update an address
- `DELETE /v1/addresses/{address_id}` - Delete an address

### Profile Management

- `GET /v1/profiles/customer` - Get customer profile
- `PUT /v1/profiles/customer` - Update customer profile
- `GET /v1/profiles/notification-settings` - Get notification settings
- `PUT /v1/profiles/notification-settings` - Update notification settings

### Restaurant Discovery

- `GET /v1/restaurants/nearby` - Get nearby restaurants
- `GET /v1/restaurants/{restaurant_id}/menu` - Get restaurant menu
- `GET /v1/restaurants/{restaurant_id}/delivery-map` - Get delivery route map
- `GET /v1/restaurants/{restaurant_id}/delivery-estimate` - Get delivery time estimate

### Order Management

- `POST /v1/orders` - Create a new order
- `POST /v1/orders/payment` - Process payment
- `GET /v1/orders` - Get user orders
- `GET /v1/orders/{order_id}` - Get order details
- `GET /v1/orders/{order_id}/tracking` - Track order
- `POST /v1/orders/{order_id}/cancel` - Cancel order

### Maps

- `GET /v1/maps/restaurant-to-address` - Show map with delivery route

## Technical Details

### Database Schema

The service uses PostgreSQL with PostGIS extension for geospatial data. Main tables:

- `users` - User account information
- `roles` - User roles (customer, restaurant, driver, admin)
- `user_roles` - Many-to-many relationship between users and roles
- `addresses` - User addresses with geospatial data
- `customer_profiles` - Customer-specific profile data
- `notification_settings` - User notification preferences

### External Integrations

- **Yandex Maps API** - For geocoding, route planning, and travel time estimation
- **Restaurant Service** - For restaurant data
- **Order Service** - For order management
- **Driver Service** - For driver tracking

### Dependencies

- FastAPI - Web framework
- Asyncpg - PostgreSQL client
- Pydantic - Data validation
- PyJWT - JWT token handling
- Aiohttp - HTTP client for service communication

## Configuration

Environment variables:

- `DATABASE_URL` - PostgreSQL connection string
- `JWT_SECRET` - Secret for JWT tokens
- `REDIS_URL` - Redis connection string for caching and token storage
- `KAFKA_BOOTSTRAP_SERVERS` - Kafka connection for event publishing
- `YANDEX_MAP_API_KEY` - API key for Yandex Maps

## Development Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

2. Run the service:
   ```bash
   uvicorn app.main:app --reload
   ```

3. Access the API documentation:
   http://localhost:8000/docs

## Docker

The service can be run in a Docker container using the provided Dockerfile:

```bash
docker build -t user-service .
docker run -p 8000:8000 user-service
```

Or using docker-compose:

```bash
docker-compose up -d
```
