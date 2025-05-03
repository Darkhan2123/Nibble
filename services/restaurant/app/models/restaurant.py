import logging
import uuid
from typing import Dict, List, Optional, Any
import asyncpg
from datetime import datetime

from app.core.database import get_connection, transaction, fetch_one, fetch_all, execute
from app.core.redis import (
    cache_restaurant, get_cached_restaurant, invalidate_restaurant_cache,
    cache_menu_items, get_cached_menu_items, invalidate_menu_cache,
    cache_operating_hours, get_cached_operating_hours, invalidate_hours_cache,
    cache_restaurant_search, get_cached_search_results, invalidate_search_cache,
    cache_nearby_restaurants, get_cached_nearby_restaurants,
    create_search_key, create_location_key
)

logger = logging.getLogger(__name__)

class RestaurantRepository:
    """Repository for restaurant-related database operations."""
    
    async def create_restaurant(
        self,
        user_id: str,
        name: str,
        description: str,
        cuisine_type: List[str],
        price_range: int,
        phone_number: str,
        email: str,
        address_id: str,
        delivery_fee: float = 0.0,
        minimum_order_amount: float = 0.0,
        website_url: Optional[str] = None,
        logo_url: Optional[str] = None,
        banner_url: Optional[str] = None,
        commission_rate: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Create a new restaurant."""
        async with transaction() as tx:
            restaurant_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO restaurant_service.restaurant_profiles (
                id, user_id, name, description, cuisine_type, price_range,
                phone_number, email, website_url, address_id, logo_url, banner_url,
                delivery_fee, minimum_order_amount, commission_rate
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15
            )
            RETURNING *
            """
            
            try:
                async with get_connection() as conn:
                    restaurant = await conn.fetchrow(
                        query,
                        restaurant_id,
                        user_id,
                        name,
                        description,
                        cuisine_type,
                        price_range,
                        phone_number,
                        email,
                        website_url,
                        address_id,
                        logo_url,
                        banner_url,
                        delivery_fee,
                        minimum_order_amount,
                        commission_rate,
                    )
                    
                    # Add default operating hours
                    for day in range(7):  # 0-6 for Sunday to Saturday
                        await conn.execute(
                            """
                            INSERT INTO restaurant_service.restaurant_hours (
                                restaurant_id, day_of_week, open_time, close_time, is_closed
                            ) VALUES (
                                $1, $2, $3, $4, $5
                            )
                            """,
                            restaurant_id,
                            day,
                            "08:00:00",  # Default open time
                            "22:00:00",  # Default close time
                            False,       # Not closed by default
                        )
                    
                    return dict(restaurant)
            except asyncpg.UniqueViolationError as e:
                logger.error(f"Unique violation error creating restaurant: {e}")
                if "user_id" in str(e):
                    raise ValueError("User already has a restaurant")
                else:
                    raise ValueError("Restaurant could not be created due to a unique constraint violation")
            except Exception as e:
                logger.error(f"Error creating restaurant: {e}")
                raise
    
    async def get_restaurant_by_id(self, restaurant_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a restaurant by ID.
        Uses Redis caching to improve performance for frequently accessed restaurants.
        """
        # Try to get from cache first
        cached_restaurant = await get_cached_restaurant(restaurant_id)
        if cached_restaurant:
            logger.debug(f"Cache hit for restaurant {restaurant_id}")
            return cached_restaurant
        
        # If not in cache, fetch from database
        logger.debug(f"Cache miss for restaurant {restaurant_id}, fetching from database")
        query = """
        SELECT * FROM restaurant_service.restaurant_profiles
        WHERE id = $1
        """
        
        restaurant = await fetch_one(query, restaurant_id)
        
        # If found, store in cache for future requests
        if restaurant:
            await cache_restaurant(restaurant_id, restaurant)
        
        return restaurant
    
    async def get_restaurant_by_user_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a restaurant by user ID."""
        query = """
        SELECT * FROM restaurant_service.restaurant_profiles
        WHERE user_id = $1
        """
        
        return await fetch_one(query, user_id)
    
    async def update_restaurant(
        self,
        restaurant_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a restaurant.
        Invalidates the restaurant cache and search cache after updating.
        """
        # Only allow updating certain fields
        allowed_fields = {
            "name", "description", "cuisine_type", "price_range", "phone_number",
            "email", "website_url", "logo_url", "banner_url", "delivery_fee",
            "minimum_order_amount", "is_active", "estimated_delivery_time"
        }
        
        # Filter out fields that are not allowed to be updated
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not filtered_data:
            return await self.get_restaurant_by_id(restaurant_id)
        
        # Construct the SQL SET clause
        set_clauses = []
        values = []
        params_index = 1
        
        for field, value in filtered_data.items():
            set_clauses.append(f"{field} = ${params_index}")
            values.append(value)
            params_index += 1
        
        set_clause = ", ".join(set_clauses)
        
        # Construct the full query
        query = f"""
        UPDATE restaurant_service.restaurant_profiles
        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
        WHERE id = ${params_index}
        RETURNING *
        """
        
        values.append(restaurant_id)
        
        try:
            restaurant = await fetch_one(query, *values)
            
            if restaurant:
                # Invalidate the restaurant cache
                await invalidate_restaurant_cache(restaurant_id)
                
                # Also invalidate search cache as restaurant info can affect search results
                await invalidate_search_cache()
            
            return restaurant
        except Exception as e:
            logger.error(f"Error updating restaurant: {e}")
            raise
    
    async def delete_restaurant(self, restaurant_id: str) -> bool:
        """Delete a restaurant."""
        query = """
        DELETE FROM restaurant_service.restaurant_profiles
        WHERE id = $1
        """
        
        result = await execute(query, restaurant_id)
        return "DELETE 1" in result
    
    async def update_restaurant_status(
        self,
        restaurant_id: str,
        is_active: bool
    ) -> Optional[Dict[str, Any]]:
        """Update a restaurant's active status."""
        query = """
        UPDATE restaurant_service.restaurant_profiles
        SET is_active = $1, updated_at = CURRENT_TIMESTAMP
        WHERE id = $2
        RETURNING *
        """
        
        return await fetch_one(query, is_active, restaurant_id)
    
    async def get_operating_hours(self, restaurant_id: str) -> List[Dict[str, Any]]:
        """
        Get operating hours for a restaurant.
        Uses Redis caching as operating hours don't change frequently.
        """
        # Try to get from cache first
        cached_hours = await get_cached_operating_hours(restaurant_id)
        if cached_hours:
            logger.debug(f"Cache hit for operating hours of restaurant {restaurant_id}")
            return cached_hours
        
        # If not in cache, fetch from database
        logger.debug(f"Cache miss for operating hours of restaurant {restaurant_id}, fetching from database")
        query = """
        SELECT * FROM restaurant_service.restaurant_hours
        WHERE restaurant_id = $1
        ORDER BY day_of_week
        """
        
        hours = await fetch_all(query, restaurant_id)
        
        # Cache the operating hours with a longer TTL (24 hours)
        if hours:
            await cache_operating_hours(restaurant_id, hours)
        
        return hours
    
    async def update_operating_hours(
        self,
        restaurant_id: str,
        day_of_week: int,
        open_time: str,
        close_time: str,
        is_closed: bool
    ) -> Dict[str, Any]:
        """
        Update operating hours for a specific day.
        Invalidates the operating hours cache after updating.
        """
        query = """
        UPDATE restaurant_service.restaurant_hours
        SET open_time = $1, close_time = $2, is_closed = $3
        WHERE restaurant_id = $4 AND day_of_week = $5
        RETURNING *
        """
        
        result = await fetch_one(
            query,
            open_time,
            close_time,
            is_closed,
            restaurant_id,
            day_of_week
        )
        
        # Invalidate the operating hours cache
        if result:
            await invalidate_hours_cache(restaurant_id)
            
            # Also invalidate search cache as operating hours can affect search results
            # (especially when searching for restaurants that are open)
            await invalidate_search_cache()
        
        return result
    
    async def search_restaurants(
        self,
        query_string: Optional[str] = None,
        cuisine_type: Optional[List[str]] = None,
        price_range: Optional[List[int]] = None,
        is_open: Optional[bool] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        radius: Optional[int] = None,
        limit: int = 20,
        offset: int = 0,
        sort_by: str = "distance"  # Can be "distance", "rating", "price"
    ) -> List[Dict[str, Any]]:
        """
        Search for restaurants based on various criteria.
        Uses PostGIS for geospatial queries when location is provided.
        Uses Redis caching to improve performance for common searches.
        """
        # Check if we can use cache for this search
        use_cache = True
        
        # Don't use cache for paginated results beyond first page
        if offset > 0:
            use_cache = False
            
        # Create cache keys for this search
        base_search_key = create_search_key(
            query_string=query_string,
            cuisine_type=cuisine_type,
            price_range=price_range,
            is_open=is_open,
            sort_by=sort_by
        )
        
        # If location is provided, create a location-specific key
        location_key = None
        if latitude is not None and longitude is not None:
            location_key = create_location_key(latitude, longitude, radius)
            
            # Check if we have cached results for this location
            if use_cache:
                location_search_key = f"{base_search_key}:{location_key}:limit:{limit}"
                cached_results = await get_cached_search_results(location_search_key)
                if cached_results:
                    logger.debug(f"Cache hit for restaurant search: {location_search_key}")
                    return cached_results
        elif use_cache:
            # Check if we have cached results for non-location search
            cached_results = await get_cached_search_results(f"{base_search_key}:limit:{limit}")
            if cached_results:
                logger.debug(f"Cache hit for restaurant search: {base_search_key}")
                return cached_results
        
        # If we reach here, we need to perform the database query
        logger.debug("Cache miss for restaurant search, querying database")
        
        conditions = ["r.is_active = TRUE"]
        params = []
        param_index = 1
        joins = []
        select_fields = ["r.*"]
        
        # Add search query condition
        if query_string:
            conditions.append(f"""
                (
                    r.name ILIKE ${param_index} OR
                    r.description ILIKE ${param_index}
                )
            """)
            params.append(f"%{query_string}%")
            param_index += 1
        
        # Add cuisine type condition
        if cuisine_type:
            cuisine_placeholders = []
            for cuisine in cuisine_type:
                cuisine_placeholders.append(f"${param_index}")
                params.append(cuisine)
                param_index += 1
            
            conditions.append(f"r.cuisine_type && ARRAY[{', '.join(cuisine_placeholders)}]::VARCHAR[]")
        
        # Add price range condition
        if price_range:
            price_placeholders = []
            for price in price_range:
                price_placeholders.append(f"${param_index}")
                params.append(price)
                param_index += 1
            
            conditions.append(f"r.price_range IN ({', '.join(price_placeholders)})")
        
        # Add location-based search with radius
        if latitude is not None and longitude is not None:
            # Join with the address table to get location
            joins.append("JOIN user_service.addresses a ON r.address_id = a.id")
            
            # If radius is provided, add a distance filter
            if radius:
                # ST_DWithin checks if a point is within a specified distance
                conditions.append(f"""
                    ST_DWithin(
                        a.location,
                        ST_SetSRID(ST_MakePoint(${param_index}, ${param_index + 1}), 4326),
                        ${param_index + 2}
                    )
                """)
                params.append(longitude)  # PostGIS uses lon, lat order
                params.append(latitude)
                params.append(radius)
                param_index += 3
            
            # Calculate distance for each restaurant
            select_fields.append(f"""
                ST_Distance(
                    a.location,
                    ST_SetSRID(ST_MakePoint(${param_index}, ${param_index + 1}), 4326)
                ) AS distance
            """)
            params.append(longitude)
            params.append(latitude)
            param_index += 2
        
        # Add "open now" condition if requested
        if is_open:
            # Get current time and day of week
            now = datetime.now()
            day_of_week = now.weekday() + 1  # Convert to 1-7 (Mon-Sun)
            if day_of_week == 7:  # Sunday should be 0
                day_of_week = 0
            
            current_time = now.strftime("%H:%M:%S")
            
            # Join with operating hours table
            joins.append("""
                JOIN restaurant_service.restaurant_hours h 
                ON r.id = h.restaurant_id AND h.day_of_week = ${param_index}
            """)
            params.append(day_of_week)
            param_index += 1
            
            # Add conditions for open hours and not closed
            conditions.append(f"""
                h.is_closed = FALSE AND
                h.open_time <= ${param_index} AND
                h.close_time >= ${param_index}
            """)
            params.append(current_time)
            param_index += 1
        
        # Build the complete query
        join_clause = " ".join(joins)
        where_clause = " AND ".join(conditions)
        select_clause = ", ".join(select_fields)
        
        # Determine sort order
        if sort_by == "distance" and latitude is not None and longitude is not None:
            order_by = "distance ASC"
        elif sort_by == "rating":
            order_by = "r.average_rating DESC"
        elif sort_by == "price":
            order_by = "r.price_range ASC"
        else:
            order_by = "r.is_featured DESC, r.average_rating DESC, r.name"
            
        # Add hours to each restaurant
        hours_subquery = """
            (SELECT json_agg(h.*) FROM restaurant_service.restaurant_hours h 
             WHERE h.restaurant_id = r.id) AS hours
        """
        
        # Add address to each restaurant
        address_subquery = """
            (SELECT json_build_object(
                'id', a.id, 
                'street', a.street, 
                'city', a.city, 
                'state', a.state, 
                'postal_code', a.postal_code, 
                'country', a.country,
                'latitude', ST_Y(a.location),
                'longitude', ST_X(a.location)
            )) AS address
        """
        
        # Construct the final query
        query = f"""
        SELECT {select_clause}, {hours_subquery}, {address_subquery}
        FROM restaurant_service.restaurant_profiles r
        {join_clause}
        WHERE {where_clause}
        ORDER BY {order_by}
        LIMIT ${param_index}
        OFFSET ${param_index + 1}
        """
        
        params.extend([limit, offset])
        
        # Execute query
        restaurants = await fetch_all(query, *params)
        
        # Process results
        for restaurant in restaurants:
            # Convert PostGIS geometry to standard lat/long
            if "address" in restaurant and restaurant["address"]:
                location = restaurant["address"]
                restaurant["distance_km"] = restaurant.get("distance", 0) / 1000  # Convert to kilometers
                
                # Add formatted address
                address_parts = []
                if location.get("street"):
                    address_parts.append(location["street"])
                if location.get("city"):
                    address_parts.append(location["city"])
                if location.get("state"):
                    address_parts.append(location["state"])
                if location.get("postal_code"):
                    address_parts.append(location["postal_code"])
                
                restaurant["formatted_address"] = ", ".join(address_parts)
        
        # Cache the results if we're on the first page
        if use_cache and restaurants:
            cache_ttl = 600  # 10 minutes default TTL
            
            if location_key:
                # Location-based searches cached with location key
                location_search_key = f"{base_search_key}:{location_key}:limit:{limit}"
                await cache_restaurant_search(location_search_key, restaurants, cache_ttl)
                
                # Also cache in the nearby restaurants cache for this location
                await cache_nearby_restaurants(location_key, restaurants, 1800)  # 30 minutes TTL
            else:
                # Non-location searches
                await cache_restaurant_search(f"{base_search_key}:limit:{limit}", restaurants, cache_ttl)
        
        return restaurants
    
    async def get_restaurant_analytics(
        self,
        restaurant_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get analytics for a restaurant.
        
        This would typically query the analytics service or data warehouse,
        but for now we'll return placeholder data.
        """
        # Placeholder implementation
        return {
            "total_orders": 0,
            "total_revenue": 0,
            "average_order_value": 0,
            "popular_items": [],
            "busiest_times": []
        }
        
    async def update_restaurant_rating(
        self,
        restaurant_id: str,
        new_rating: float
    ) -> Optional[Dict[str, Any]]:
        """
        Update a restaurant's average rating.
        Invalidates the restaurant cache and search cache after updating.
        """
        query = """
        UPDATE restaurant_service.restaurant_profiles
        SET 
            average_rating = (average_rating * total_ratings + $1) / (total_ratings + 1),
            total_ratings = total_ratings + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $2
        RETURNING *
        """
        
        restaurant = await fetch_one(query, new_rating, restaurant_id)
        
        if restaurant:
            # Invalidate the restaurant cache
            await invalidate_restaurant_cache(restaurant_id)
            
            # Also invalidate search cache as ratings affect search results sorting
            await invalidate_search_cache()
        
        return restaurant