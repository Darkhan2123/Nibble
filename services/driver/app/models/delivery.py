import logging
import uuid
from typing import Dict, List, Optional, Any
import asyncpg
from datetime import datetime

from app.core.database import get_connection, transaction, fetch_one, fetch_all, execute
from app.core.maps import calculate_route, estimate_delivery_time

logger = logging.getLogger(__name__)

class DeliveryRepository:
    """Repository for delivery-related database operations."""
    
    async def get_delivery_location_history(
        self,
        order_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get the location history for a delivery."""
        query = """
        SELECT 
            id,
            order_id,
            driver_id,
            ST_X(location) as longitude,
            ST_Y(location) as latitude,
            status,
            recorded_at
        FROM order_service.delivery_location_history
        WHERE order_id = $1
        ORDER BY recorded_at DESC
        LIMIT $2
        OFFSET $3
        """
        
        return await fetch_all(query, order_id, limit, offset)
    
    async def get_driver_deliveries(
        self,
        driver_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get deliveries for a driver, optionally filtered by status."""
        # In a real application, this would be a more complex query joining
        # various tables. For this demo, we're simplifying.
        conditions = ["driver_id = $1"]
        params = [driver_id]
        param_index = 2
        
        if status:
            conditions.append(f"status = ${param_index}")
            params.append(status)
            param_index += 1
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        SELECT o.*, 
               (SELECT json_agg(oi.*) FROM order_service.order_items oi 
                WHERE oi.order_id = o.id) AS items
        FROM order_service.orders o
        WHERE {where_clause}
        ORDER BY o.created_at DESC
        LIMIT ${param_index}
        OFFSET ${param_index + 1}
        """
        
        params.extend([limit, offset])
        
        return await fetch_all(query, *params)
    
    async def get_active_deliveries(
        self,
        driver_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get active deliveries for a driver."""
        # Active deliveries are those that are in the delivery stage
        active_statuses = ["ready_for_pickup", "out_for_delivery"]
        
        placeholders = []
        params = [driver_id]
        param_index = 2
        
        for _ in active_statuses:
            placeholders.append(f"${param_index}")
            params.append(_)
            param_index += 1
        
        query = f"""
        SELECT o.*, 
               (SELECT json_agg(oi.*) FROM order_service.order_items oi 
                WHERE oi.order_id = o.id) AS items
        FROM order_service.orders o
        WHERE driver_id = $1
          AND status IN ({", ".join(placeholders)})
        ORDER BY o.created_at DESC
        LIMIT ${param_index}
        OFFSET ${param_index + 1}
        """
        
        params.extend([limit, offset])
        
        return await fetch_all(query, *params)
    
    async def get_delivery(
        self,
        order_id: str,
        driver_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific delivery by order ID."""
        query = """
        SELECT o.*, 
               (SELECT json_agg(oi.*) FROM order_service.order_items oi 
                WHERE oi.order_id = o.id) AS items
        FROM order_service.orders o
        WHERE o.id = $1 AND o.driver_id = $2
        """
        
        return await fetch_one(query, order_id, driver_id)
    
    async def update_delivery_status(
        self,
        order_id: str,
        driver_id: str,
        status: str,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a delivery's status."""
        # Valid status transitions for a driver
        valid_status_transitions = {
            "ready_for_pickup": ["out_for_delivery", "cancelled"],
            "out_for_delivery": ["delivered", "cancelled"]
        }
        
        # Get the current order
        query_current = """
        SELECT * FROM order_service.orders
        WHERE id = $1 AND driver_id = $2
        """
        
        current_order = await fetch_one(query_current, order_id, driver_id)
        
        if not current_order:
            logger.error(f"Order {order_id} not found for driver {driver_id}")
            return None
        
        current_status = current_order["status"]
        
        # Check if the transition is valid
        if current_status not in valid_status_transitions or status not in valid_status_transitions.get(current_status, []):
            logger.error(f"Invalid status transition from {current_status} to {status}")
            raise ValueError(f"Invalid status transition from {current_status} to {status}")
        
        # Update the order status
        query = """
        UPDATE order_service.orders
        SET status = $1, updated_at = CURRENT_TIMESTAMP
        """
        
        params = [status, order_id, driver_id]
        param_index = 4
        
        # If it's delivered, add actual delivery time
        if status == "delivered":
            query += ", actual_delivery_time = CURRENT_TIMESTAMP"
        
        # Add location if provided
        if latitude is not None and longitude is not None:
            query += ", current_location = ST_SetSRID(ST_MakePoint($4, $5), 4326)"
            params.insert(3, longitude)  # PostGIS expects (lon, lat) order
            params.insert(4, latitude)
            param_index += 2
        
        query += f" WHERE id = $2 AND driver_id = $3 RETURNING *"
        
        updated_order = await fetch_one(query, *params)
        
        if updated_order:
            # Record the status change in history
            history_query = """
            INSERT INTO order_service.order_status_history (
                order_id, status, updated_by_user_id, notes
            ) VALUES (
                $1, $2, $3, $4
            )
            """
            
            await execute(
                history_query,
                order_id,
                status,
                driver_id,
                notes
            )
        
        return updated_order
    
    async def assign_delivery(
        self,
        order_id: str,
        driver_id: str
    ) -> Optional[Dict[str, Any]]:
        """Assign a delivery to a driver."""
        # Check if order exists and is ready for pickup
        query_order = """
        SELECT * FROM order_service.orders
        WHERE id = $1 AND status = 'ready_for_pickup' AND driver_id IS NULL
        """
        
        order = await fetch_one(query_order, order_id)
        
        if not order:
            logger.error(f"Order {order_id} not found or not ready for pickup")
            return None
        
        # Check if driver exists and is available
        query_driver = """
        SELECT * FROM driver_service.driver_profiles
        WHERE user_id = $1 AND is_available = TRUE
        """
        
        driver = await fetch_one(query_driver, driver_id)
        
        if not driver:
            logger.error(f"Driver {driver_id} not found or not available")
            return None
        
        # Assign the driver to the order
        query_assign = """
        UPDATE order_service.orders
        SET driver_id = $1, updated_at = CURRENT_TIMESTAMP
        WHERE id = $2
        RETURNING *
        """
        
        updated_order = await fetch_one(query_assign, driver_id, order_id)
        
        if updated_order:
            # Record the assignment in history
            history_query = """
            INSERT INTO order_service.order_status_history (
                order_id, status, updated_by_user_id, notes
            ) VALUES (
                $1, $2, $3, $4
            )
            """
            
            await execute(
                history_query,
                order_id,
                updated_order["status"],
                driver_id,
                "Delivery assigned to driver"
            )
        
        return updated_order
    
    async def calculate_delivery_route(
        self,
        order_id: str,
        driver_id: str,
        avoid_tolls: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Calculate the delivery route for an order.
        This would typically call an external routing service.
        For now, we'll return a simplified route.
        """
        # Get the order with delivery address
        query_order = """
        SELECT o.*, a.location AS delivery_location
        FROM order_service.orders o
        JOIN user_service.addresses a ON o.delivery_address_id = a.id
        WHERE o.id = $1 AND o.driver_id = $2
        """
        
        order = await fetch_one(query_order, order_id, driver_id)
        
        if not order or "delivery_location" not in order:
            logger.error(f"Order {order_id} not found or missing delivery location")
            return None
        
        # Get the restaurant location
        query_restaurant = """
        SELECT r.*, a.location AS restaurant_location
        FROM restaurant_service.restaurant_profiles r
        JOIN user_service.addresses a ON r.address_id = a.id
        WHERE r.id = $1
        """
        
        restaurant = await fetch_one(query_restaurant, order["restaurant_id"])
        
        if not restaurant or "restaurant_location" not in restaurant:
            logger.error(f"Restaurant {order['restaurant_id']} not found or missing location")
            return None
        
        # Get driver's current location
        query_driver = """
        SELECT ST_X(current_location) AS longitude, ST_Y(current_location) AS latitude
        FROM driver_service.driver_profiles
        WHERE user_id = $1
        """
        
        driver_location = await fetch_one(query_driver, driver_id)
        
        if not driver_location or "latitude" not in driver_location:
            logger.error(f"Driver {driver_id} location not found")
            return None
        
        # Extract coordinates
        driver_lat = float(driver_location["latitude"])
        driver_lon = float(driver_location["longitude"])
        
        restaurant_location = restaurant["restaurant_location"]
        restaurant_lat = float(restaurant_location["y"])
        restaurant_lon = float(restaurant_location["x"])
        
        delivery_location = order["delivery_location"]
        delivery_lat = float(delivery_location["y"])
        delivery_lon = float(delivery_location["x"])
        
        # Calculate route using Yandex Maps API
        route_to_restaurant = await calculate_route(
            driver_lat, driver_lon, restaurant_lat, restaurant_lon, avoid_tolls
        )
        
        route_to_customer = await calculate_route(
            restaurant_lat, restaurant_lon, delivery_lat, delivery_lon, avoid_tolls
        )
        
        if not route_to_restaurant or not route_to_customer:
            logger.error(f"Error calculating route for order {order_id}")
            return None
        
        # Calculate total distance and ETA
        total_distance = route_to_restaurant["distance"] + route_to_customer["distance"]
        
        estimated_pickup_time = route_to_restaurant["duration"] / 60  # minutes
        estimated_delivery_time = route_to_customer["duration"] / 60  # minutes
        total_time = estimated_pickup_time + estimated_delivery_time
        
        # Include 5 minute buffer for restaurant pickup
        total_time += 5
        
        return {
            "order_id": order_id,
            "driver_id": driver_id,
            "route_to_restaurant": {
                "distance": route_to_restaurant["distance"],
                "duration": route_to_restaurant["duration"],
                "polyline": route_to_restaurant["polyline"],
                "source": route_to_restaurant.get("source", "simplified_calculation")
            },
            "route_to_customer": {
                "distance": route_to_customer["distance"],
                "duration": route_to_customer["duration"],
                "polyline": route_to_customer["polyline"],
                "source": route_to_customer.get("source", "simplified_calculation")
            },
            "total_distance": total_distance,
            "estimated_pickup_time": estimated_pickup_time,
            "estimated_delivery_time": estimated_delivery_time,
            "total_time": total_time,
            "avoid_tolls": avoid_tolls
        }