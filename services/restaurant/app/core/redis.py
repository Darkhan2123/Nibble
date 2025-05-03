import redis.asyncio as redis
import logging
import json
from typing import Optional, Dict, List, Any

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global Redis pool
redis_pool: Optional[redis.ConnectionPool] = None

async def init_redis() -> None:
    """Initialize the Redis connection pool."""
    global redis_pool
    try:
        logger.info("Creating Redis connection pool")
        redis_pool = redis.ConnectionPool.from_url(settings.REDIS_URL)
        logger.info("Redis connection pool created successfully")
    except Exception as e:
        logger.error(f"Failed to create Redis connection pool: {e}")
        raise

async def get_redis_client() -> redis.Redis:
    """Get a Redis client."""
    global redis_pool
    if redis_pool is None:
        await init_redis()
    
    return redis.Redis(connection_pool=redis_pool)

async def get_redis():
    """Dependency to get a Redis client."""
    client = await get_redis_client()
    try:
        yield client
    finally:
        await client.close()

# Restaurant-specific Redis functions
async def cache_restaurant(restaurant_id: str, restaurant_data: dict, ttl: int = 3600) -> None:
    """Cache restaurant data in Redis."""
    redis_client = await get_redis_client()
    try:
        await redis_client.setex(
            f"restaurant:{restaurant_id}",
            ttl,
            json.dumps(restaurant_data)
        )
        logger.info(f"Restaurant {restaurant_id} data cached successfully")
    except Exception as e:
        logger.error(f"Failed to cache restaurant data: {e}")

async def get_cached_restaurant(restaurant_id: str) -> Optional[dict]:
    """Get cached restaurant data from Redis."""
    redis_client = await get_redis_client()
    try:
        data = await redis_client.get(f"restaurant:{restaurant_id}")
        if data:
            logger.debug(f"Cache hit for restaurant {restaurant_id}")
            return json.loads(data)
        logger.debug(f"Cache miss for restaurant {restaurant_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached restaurant: {e}")
        return None

async def invalidate_restaurant_cache(restaurant_id: str) -> None:
    """Invalidate restaurant cache in Redis."""
    redis_client = await get_redis_client()
    try:
        await redis_client.delete(f"restaurant:{restaurant_id}")
        logger.info(f"Cache invalidated for restaurant {restaurant_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate restaurant cache: {e}")

async def cache_menu_items(restaurant_id: str, menu_items: list, ttl: int = 3600) -> None:
    """Cache menu items in Redis."""
    redis_client = await get_redis_client()
    try:
        await redis_client.setex(
            f"restaurant:{restaurant_id}:menu",
            ttl,
            json.dumps(menu_items)
        )
        logger.info(f"Menu items for restaurant {restaurant_id} cached successfully")
    except Exception as e:
        logger.error(f"Failed to cache menu items: {e}")

async def get_cached_menu_items(restaurant_id: str) -> Optional[list]:
    """Get cached menu items from Redis."""
    redis_client = await get_redis_client()
    try:
        data = await redis_client.get(f"restaurant:{restaurant_id}:menu")
        if data:
            logger.debug(f"Cache hit for menu items of restaurant {restaurant_id}")
            return json.loads(data)
        logger.debug(f"Cache miss for menu items of restaurant {restaurant_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached menu items: {e}")
        return None

async def invalidate_menu_cache(restaurant_id: str) -> None:
    """Invalidate menu cache in Redis."""
    redis_client = await get_redis_client()
    try:
        await redis_client.delete(f"restaurant:{restaurant_id}:menu")
        logger.info(f"Menu cache invalidated for restaurant {restaurant_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate menu cache: {e}")

# Additional caching functions for restaurant search results
async def cache_restaurant_search(search_key: str, results: List[Dict[str, Any]], ttl: int = 600) -> None:
    """
    Cache restaurant search results.
    search_key: A unique key derived from the search parameters
    results: The search results to cache
    ttl: Cache TTL in seconds (default 10 minutes)
    """
    redis_client = await get_redis_client()
    try:
        await redis_client.setex(
            f"search:restaurants:{search_key}",
            ttl,
            json.dumps(results)
        )
        logger.info(f"Search results cached with key {search_key}")
    except Exception as e:
        logger.error(f"Failed to cache search results: {e}")

async def get_cached_search_results(search_key: str) -> Optional[List[Dict[str, Any]]]:
    """
    Get cached restaurant search results.
    search_key: The search key used when caching the results
    """
    redis_client = await get_redis_client()
    try:
        data = await redis_client.get(f"search:restaurants:{search_key}")
        if data:
            logger.debug(f"Cache hit for search key {search_key}")
            return json.loads(data)
        logger.debug(f"Cache miss for search key {search_key}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached search results: {e}")
        return None

async def invalidate_search_cache() -> None:
    """
    Invalidate all restaurant search caches.
    This should be called when restaurants are updated that might affect search results.
    """
    redis_client = await get_redis_client()
    try:
        # Delete all keys matching the search pattern
        cursor = '0'
        while cursor != 0:
            cursor, keys = await redis_client.scan(cursor=cursor, match="search:restaurants:*", count=100)
            if keys:
                await redis_client.delete(*keys)
        logger.info("All restaurant search caches invalidated")
    except Exception as e:
        logger.error(f"Failed to invalidate search cache: {e}")

# Caching for restaurant operating hours
async def cache_operating_hours(restaurant_id: str, hours_data: List[Dict[str, Any]], ttl: int = 86400) -> None:
    """
    Cache restaurant operating hours.
    These change infrequently, so we use a longer TTL (24 hours by default).
    """
    redis_client = await get_redis_client()
    try:
        await redis_client.setex(
            f"restaurant:{restaurant_id}:hours",
            ttl,
            json.dumps(hours_data)
        )
        logger.info(f"Operating hours for restaurant {restaurant_id} cached successfully")
    except Exception as e:
        logger.error(f"Failed to cache operating hours: {e}")

async def get_cached_operating_hours(restaurant_id: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached operating hours for a restaurant."""
    redis_client = await get_redis_client()
    try:
        data = await redis_client.get(f"restaurant:{restaurant_id}:hours")
        if data:
            logger.debug(f"Cache hit for operating hours of restaurant {restaurant_id}")
            return json.loads(data)
        logger.debug(f"Cache miss for operating hours of restaurant {restaurant_id}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached operating hours: {e}")
        return None

async def invalidate_hours_cache(restaurant_id: str) -> None:
    """Invalidate operating hours cache for a restaurant."""
    redis_client = await get_redis_client()
    try:
        await redis_client.delete(f"restaurant:{restaurant_id}:hours")
        logger.info(f"Operating hours cache invalidated for restaurant {restaurant_id}")
    except Exception as e:
        logger.error(f"Failed to invalidate operating hours cache: {e}")

# Caching for nearby restaurants based on location
async def cache_nearby_restaurants(location_key: str, results: List[Dict[str, Any]], ttl: int = 1800) -> None:
    """
    Cache nearby restaurants for a given location.
    location_key: A string key derived from latitude and longitude (e.g., "lat:34.052235:lon:-118.243683:radius:5")
    results: The list of nearby restaurants to cache
    ttl: Cache TTL in seconds (default 30 minutes)
    """
    redis_client = await get_redis_client()
    try:
        await redis_client.setex(
            f"nearby:restaurants:{location_key}",
            ttl,
            json.dumps(results)
        )
        logger.info(f"Nearby restaurants cached for location {location_key}")
    except Exception as e:
        logger.error(f"Failed to cache nearby restaurants: {e}")

async def get_cached_nearby_restaurants(location_key: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached nearby restaurants for a given location."""
    redis_client = await get_redis_client()
    try:
        data = await redis_client.get(f"nearby:restaurants:{location_key}")
        if data:
            logger.debug(f"Cache hit for nearby restaurants at location {location_key}")
            return json.loads(data)
        logger.debug(f"Cache miss for nearby restaurants at location {location_key}")
        return None
    except Exception as e:
        logger.error(f"Error retrieving cached nearby restaurants: {e}")
        return None

# Function to create a hash of search parameters for consistent cache keys
def create_search_key(
    query_string: Optional[str] = None,
    cuisine_type: Optional[List[str]] = None,
    price_range: Optional[List[int]] = None,
    is_open: Optional[bool] = None,
    sort_by: str = "distance"
) -> str:
    """
    Create a unique cache key based on search parameters.
    Exclude location parameters as they're handled separately.
    """
    key_parts = []
    
    if query_string:
        key_parts.append(f"q:{query_string}")
    
    if cuisine_type:
        sorted_cuisines = sorted(cuisine_type)
        key_parts.append(f"cuisine:{','.join(sorted_cuisines)}")
    
    if price_range:
        sorted_prices = sorted(price_range)
        key_parts.append(f"price:{','.join(map(str, sorted_prices))}")
    
    if is_open is not None:
        key_parts.append(f"open:{is_open}")
    
    key_parts.append(f"sort:{sort_by}")
    
    # Create a unique key from all parameters
    if key_parts:
        return ":".join(key_parts)
    
    return "all"  # Default key for no search parameters

def create_location_key(latitude: float, longitude: float, radius: Optional[int] = None) -> str:
    """
    Create a cache key for location-based searches.
    We round coordinates to reduce the number of unique cache keys.
    """
    # Round coordinates to 3 decimal places (approximately 110m precision)
    lat_rounded = round(latitude, 3)
    lon_rounded = round(longitude, 3)
    
    if radius:
        return f"lat:{lat_rounded}:lon:{lon_rounded}:radius:{radius}"
    
    return f"lat:{lat_rounded}:lon:{lon_rounded}"