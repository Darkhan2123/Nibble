import logging
import uuid
from typing import Dict, List, Optional, Any
import asyncpg
from datetime import datetime, date

from app.core.database import get_connection, transaction, fetch_one, fetch_all, execute
from app.core.maps import calculate_distance

logger = logging.getLogger(__name__)

class DriverRepository:
    """Repository for driver-related database operations."""
    
    async def create_driver_profile(
        self,
        user_id: str,
        vehicle_type: str,
        vehicle_make: Optional[str] = None,
        vehicle_model: Optional[str] = None,
        vehicle_year: Optional[int] = None,
        license_plate: Optional[str] = None,
        driver_license_number: Optional[str] = None,
        driver_license_expiry: Optional[date] = None,
        insurance_number: Optional[str] = None,
        insurance_expiry: Optional[date] = None,
        banking_info: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Create a new driver profile."""
        query = """
        INSERT INTO driver_service.driver_profiles (
            user_id, vehicle_type, vehicle_make, vehicle_model, vehicle_year,
            license_plate, driver_license_number, driver_license_expiry,
            insurance_number, insurance_expiry, banking_info
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11
        )
        RETURNING *
        """
        
        try:
            return await fetch_one(
                query,
                user_id,
                vehicle_type,
                vehicle_make,
                vehicle_model,
                vehicle_year,
                license_plate,
                driver_license_number,
                driver_license_expiry,
                insurance_number,
                insurance_expiry,
                banking_info
            )
        except asyncpg.UniqueViolationError:
            logger.error(f"Driver profile already exists for user {user_id}")
            raise ValueError("Driver profile already exists for this user")
        except Exception as e:
            logger.error(f"Error creating driver profile: {e}")
            raise
    
    async def get_driver_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a driver by user ID."""
        query = """
        SELECT * FROM driver_service.driver_profiles
        WHERE user_id = $1
        """
        
        return await fetch_one(query, user_id)
    
    async def update_driver_profile(
        self,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a driver profile."""
        # Only allow updating certain fields
        allowed_fields = {
            "vehicle_type", "vehicle_make", "vehicle_model", "vehicle_year",
            "license_plate", "driver_license_number", "driver_license_expiry",
            "insurance_number", "insurance_expiry", "banking_info",
            "is_available"
        }
        
        # Filter out fields that are not allowed to be updated
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not filtered_data:
            return await self.get_driver_by_id(user_id)
        
        # Construct the SQL SET clause
        set_clauses = []
        values = []
        params_index = 1
        
        for field, value in filtered_data.items():
            set_clauses.append(f"{field} = ${params_index}")
            values.append(value)
            params_index += 1
        
        set_clause = ", ".join(set_clauses)
        
        # Add updated_at field
        set_clauses.append(f"updated_at = CURRENT_TIMESTAMP")
        
        # Construct the full query
        query = f"""
        UPDATE driver_service.driver_profiles
        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ${params_index}
        RETURNING *
        """
        
        values.append(user_id)
        
        try:
            return await fetch_one(query, *values)
        except Exception as e:
            logger.error(f"Error updating driver profile: {e}")
            raise
    
    async def update_driver_location(
        self,
        user_id: str,
        latitude: float,
        longitude: float,
        is_available: Optional[bool] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a driver's current location."""
        query_parts = ["current_location = ST_SetSRID(ST_MakePoint($1, $2), 4326)"]
        params = [longitude, latitude, user_id]  # Note: PostGIS expects (lon, lat) order
        
        # Include availability status if provided
        if is_available is not None:
            query_parts.append("is_available = $4")
            params.insert(3, is_available)
        
        # Construct the full query
        query = f"""
        UPDATE driver_service.driver_profiles
        SET {", ".join(query_parts)}, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = ${len(params)}
        RETURNING *
        """
        
        try:
            return await fetch_one(query, *params)
        except Exception as e:
            logger.error(f"Error updating driver location: {e}")
            raise
    
    async def update_driver_availability(
        self,
        user_id: str,
        is_available: bool
    ) -> Optional[Dict[str, Any]]:
        """Update a driver's availability status."""
        query = """
        UPDATE driver_service.driver_profiles
        SET is_available = $1, updated_at = CURRENT_TIMESTAMP
        WHERE user_id = $2
        RETURNING *
        """
        
        try:
            return await fetch_one(query, is_available, user_id)
        except Exception as e:
            logger.error(f"Error updating driver availability: {e}")
            raise
    
    async def get_nearby_drivers(
        self,
        latitude: float,
        longitude: float,
        radius: int = 5000,  # meters
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get drivers within a specified radius.
        This uses PostGIS ST_DWithin to find drivers within the radius.
        """
        query = """
        SELECT 
            d.*,
            ST_Distance(
                d.current_location, 
                ST_SetSRID(ST_MakePoint($1, $2), 4326)
            ) AS distance
        FROM driver_service.driver_profiles d
        WHERE 
            d.is_available = TRUE
            AND d.current_location IS NOT NULL
            AND ST_DWithin(
                d.current_location,
                ST_SetSRID(ST_MakePoint($1, $2), 4326),
                $3
            )
        ORDER BY distance
        LIMIT $4
        """
        
        try:
            return await fetch_all(query, longitude, latitude, radius, limit)
        except Exception as e:
            logger.error(f"Error finding nearby drivers: {e}")
            raise
    
    async def get_driver_statistics(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get statistics for a driver.
        This would typically include delivery counts, earnings, ratings, etc.
        For now, we'll return placeholder data.
        """
        # Calculate total deliveries and average rating
        query = """
        SELECT
            COUNT(*) AS total_deliveries,
            AVG(r.delivery_rating) AS average_rating,
            SUM(o.total_amount * 0.1) AS total_earnings, -- Assume 10% commission
            SUM(o.tip) AS total_tips
        FROM order_service.orders o
        LEFT JOIN order_service.ratings r ON o.id = r.order_id
        WHERE 
            o.driver_id = $1
            AND o.status IN ('delivered', 'picked_up')
        """
        
        params = [user_id]
        param_index = 2
        
        # Add date filters if provided
        if start_date:
            query += f" AND o.created_at >= ${param_index}"
            params.append(start_date)
            param_index += 1
        
        if end_date:
            query += f" AND o.created_at <= ${param_index}"
            params.append(end_date)
        
        try:
            stats = await fetch_one(query, *params)
            
            if not stats:
                # Return default values if no data
                return {
                    "total_deliveries": 0,
                    "average_rating": 0,
                    "total_earnings": 0,
                    "total_tips": 0,
                    "completion_rate": 100,  # Assume 100% completion rate for new drivers
                    "average_delivery_time": 0
                }
            
            # Calculate completion rate
            # This would compare assigned deliveries vs completed deliveries
            # For now, we'll use a placeholder value
            completion_rate = 100  # Placeholder
            
            # Calculate average delivery time
            delivery_time_query = """
            SELECT AVG(
                EXTRACT(EPOCH FROM (actual_delivery_time - created_at)) / 60
            ) AS avg_delivery_time
            FROM order_service.orders
            WHERE 
                driver_id = $1
                AND status IN ('delivered', 'picked_up')
                AND actual_delivery_time IS NOT NULL
            """
            
            delivery_time_result = await fetch_one(delivery_time_query, user_id)
            avg_delivery_time = delivery_time_result.get("avg_delivery_time", 0) if delivery_time_result else 0
            
            return {
                "total_deliveries": stats.get("total_deliveries", 0),
                "average_rating": stats.get("average_rating", 0),
                "total_earnings": stats.get("total_earnings", 0),
                "total_tips": stats.get("total_tips", 0),
                "completion_rate": completion_rate,
                "average_delivery_time": avg_delivery_time  # in minutes
            }
            
        except Exception as e:
            logger.error(f"Error getting driver statistics: {e}")
            # Return default values on error
            return {
                "total_deliveries": 0,
                "average_rating": 0,
                "total_earnings": 0,
                "total_tips": 0,
                "completion_rate": 100,
                "average_delivery_time": 0
            }
    
    async def get_driver_earnings(
        self,
        user_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Get detailed earnings information for a driver within a date range.
        Returns daily earnings breakdown.
        """
        query = """
        SELECT
            DATE_TRUNC('day', o.created_at) AS day,
            COUNT(*) AS deliveries,
            SUM(o.total_amount * 0.1) AS earnings, -- Assume 10% commission
            SUM(o.tip) AS tips
        FROM order_service.orders o
        WHERE 
            o.driver_id = $1
            AND o.status IN ('delivered', 'picked_up')
            AND o.created_at BETWEEN $2 AND $3
        GROUP BY DATE_TRUNC('day', o.created_at)
        ORDER BY day
        """
        
        try:
            return await fetch_all(query, user_id, start_date, end_date)
        except Exception as e:
            logger.error(f"Error getting driver earnings: {e}")
            return []
    
    async def update_driver_rating(
        self,
        user_id: str,
        new_rating: float
    ) -> Optional[Dict[str, Any]]:
        """Update a driver's average rating."""
        query = """
        UPDATE driver_service.driver_profiles
        SET 
            average_rating = (average_rating * total_deliveries + $1) / (total_deliveries + 1),
            total_deliveries = total_deliveries + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = $2
        RETURNING *
        """
        
        try:
            return await fetch_one(query, new_rating, user_id)
        except Exception as e:
            logger.error(f"Error updating driver rating: {e}")
            raise