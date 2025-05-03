# Driver Service

The Driver Service manages all functionality related to food delivery drivers in the UberEats clone application.

## Features

- Driver profile management
- Location tracking and updates
- Driver availability management
- Delivery assignment and management
- Route calculation and optimization (with Yandex Maps)
- Earnings tracking and statistics

## Technical Details

- Built with FastAPI
- Uses PostgreSQL with PostGIS for location data
- Integrates with Yandex Maps API for geocoding and routing
- Uses Redis for real-time location caching
- Publishes events to Kafka for system-wide communication

## API Endpoints

### Driver Profile Management

- `POST /v1/drivers/` - Create a new driver profile
- `GET /v1/drivers/me` - Get the current driver's profile
- `PUT /v1/drivers/me` - Update the current driver's profile
- `GET /v1/drivers/{driver_id}` - Get a driver's profile by ID (admin/restaurant only)

### Location Management

- `POST /v1/drivers/me/location` - Update the current driver's location
- `POST /v1/drivers/me/availability` - Update the current driver's availability
- `GET /v1/drivers/nearby` - Get nearby available drivers

### Delivery Management

- `GET /v1/deliveries/` - Get all deliveries for the current driver
- `GET /v1/deliveries/active` - Get active deliveries for the current driver
- `GET /v1/deliveries/{order_id}` - Get a specific delivery
- `POST /v1/deliveries/{order_id}/status` - Update the status of a delivery
- `GET /v1/deliveries/{order_id}/route` - Calculate the delivery route
- `POST /v1/deliveries/{order_id}/location` - Update the location of a delivery
- `GET /v1/deliveries/{order_id}/location-history` - Get the location history of a delivery

### Statistics

- `GET /v1/drivers/me/statistics` - Get statistics for the current driver
- `GET /v1/drivers/me/earnings` - Get earnings breakdown for the current driver

## Yandex Maps Integration

The Driver Service uses Yandex Maps for:

1. Geocoding addresses to coordinates
2. Calculating optimal routes for deliveries
3. Estimating delivery times based on distance and traffic
4. Visualizing delivery routes

For more details, see [Yandex Maps Integration](../../docs/yandex_maps_integration.md).

## Configuration

The service is configured via environment variables:

```
# Database
DATABASE_URL=postgresql://ubereats:ubereats_password@postgres:5432/ubereats

# Redis
REDIS_URL=redis://redis:6379/0

# Kafka
KAFKA_BOOTSTRAP_SERVERS=kafka:29092

# Yandex Maps
YANDEX_MAP_API_KEY=my api ley
```

## Setup & Development

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the service:
   ```
   uvicorn app.main:app --reload
   ```

## Database Migrations

When changes are made to the database schema, run:

```
cd infrastructure/postgres/migrations
psql -U ubereats -d ubereats -f 001_delivery_location_tracking.sql
```
