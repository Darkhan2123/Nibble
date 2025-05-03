import redis.asyncio as redis
import logging
import json
from typing import Optional, Dict, Any, List
import pickle
from datetime import datetime

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

# Driver location management
async def update_driver_location(
    driver_id: str, 
    latitude: float, 
    longitude: float, 
    is_available: bool
) -> None:
    """Update driver location in Redis."""
    redis_client = await get_redis_client()
    
    # Store driver location data
    driver_data = {
        "latitude": latitude,
        "longitude": longitude,
        "is_available": is_available,
        "last_updated": datetime.utcnow().isoformat()
    }
    
    # Set driver location in a hash
    await redis_client.hset(
        f"driver:location:{driver_id}",
        mapping=driver_data
    )
    
    # Set expiry on the hash
    await redis_client.expire(
        f"driver:location:{driver_id}",
        settings.LOCATION_EXPIRY_TIME
    )
    
    # Update geospatial index if driver is available
    if is_available:
        await redis_client.geoadd(
            "geo:drivers:active",
            (longitude, latitude, driver_id)
        )
    else:
        # Remove from active drivers if not available
        await redis_client.zrem("geo:drivers:active", driver_id)

async def get_driver_location(driver_id: str) -> Optional[Dict[str, Any]]:
    """Get driver location from Redis."""
    redis_client = await get_redis_client()
    
    location_data = await redis_client.hgetall(f"driver:location:{driver_id}")
    
    if not location_data:
        return None
    
    # Convert Redis hash to dictionary
    location = {}
    for key, value in location_data.items():
        if isinstance(key, bytes):
            key = key.decode('utf-8')
        if isinstance(value, bytes):
            value = value.decode('utf-8')
            
        # Convert values to appropriate types
        if key == 'latitude' or key == 'longitude':
            location[key] = float(value)
        elif key == 'is_available':
            location[key] = value.lower() == 'true'
        else:
            location[key] = value
    
    return location

async def get_nearby_drivers(
    latitude: float, 
    longitude: float, 
    radius: int = 5000,  # radius in meters
    limit: int = 10
) -> List[Dict[str, Any]]:
    """Get nearby available drivers within the specified radius."""
    redis_client = await get_redis_client()
    
    # Search for nearby drivers using geo radius
    nearby_drivers = await redis_client.georadius(
        "geo:drivers:active",
        longitude,
        latitude,
        radius,
        unit="m",
        withdist=True,
        withcoord=True,
        count=limit,
        sort="ASC"  # Sort by distance, closest first
    )
    
    result = []
    for driver in nearby_drivers:
        driver_id = driver[0].decode('utf-8')
        distance = driver[1]  # distance in meters
        coords = driver[2]    # [longitude, latitude]
        
        # Get driver data from hash
        driver_data = await get_driver_location(driver_id)
        
        if driver_data:
            driver_data["distance"] = distance
            driver_data["driver_id"] = driver_id
            result.append(driver_data)
    
    return result

# Driver delivery assignments
async def assign_delivery_to_driver(
    driver_id: str,
    order_id: str,
    delivery_data: Dict[str, Any]
) -> bool:
    """Assign a delivery to a driver."""
    redis_client = await get_redis_client()
    
    # Check how many active deliveries the driver has
    active_deliveries = await redis_client.hgetall(f"driver:deliveries:{driver_id}")
    
    if len(active_deliveries) >= settings.MAX_ACTIVE_DELIVERIES:
        logger.warning(f"Driver {driver_id} already has maximum active deliveries")
        return False
    
    # Add the delivery to the driver's active deliveries
    await redis_client.hset(
        f"driver:deliveries:{driver_id}",
        order_id,
        json.dumps(delivery_data)
    )
    
    # Also store the delivery by order ID for quick lookup
    await redis_client.set(
        f"delivery:order:{order_id}",
        json.dumps({
            "driver_id": driver_id,
            **delivery_data
        })
    )
    
    return True

async def get_driver_deliveries(driver_id: str) -> List[Dict[str, Any]]:
    """Get all active deliveries for a driver."""
    redis_client = await get_redis_client()
    
    deliveries_data = await redis_client.hgetall(f"driver:deliveries:{driver_id}")
    
    result = []
    for order_id, delivery_json in deliveries_data.items():
        if isinstance(order_id, bytes):
            order_id = order_id.decode('utf-8')
        if isinstance(delivery_json, bytes):
            delivery_json = delivery_json.decode('utf-8')
            
        delivery_data = json.loads(delivery_json)
        delivery_data["order_id"] = order_id
        result.append(delivery_data)
    
    return result

async def complete_delivery(driver_id: str, order_id: str) -> bool:
    """Mark a delivery as completed and remove from active deliveries."""
    redis_client = await get_redis_client()
    
    # Remove from driver's active deliveries
    removed = await redis_client.hdel(f"driver:deliveries:{driver_id}", order_id)
    
    if removed:
        # Remove from order lookup
        await redis_client.delete(f"delivery:order:{order_id}")
        return True
    
    return False

# Cache for frequently accessed data
async def cache_driver_statistics(driver_id: str, statistics: Dict[str, Any], ttl: int = 3600) -> None:
    """Cache driver statistics."""
    redis_client = await get_redis_client()
    
    await redis_client.setex(
        f"driver:stats:{driver_id}",
        ttl,
        json.dumps(statistics)
    )

async def get_cached_driver_statistics(driver_id: str) -> Optional[Dict[str, Any]]:
    """Get cached driver statistics."""
    redis_client = await get_redis_client()
    
    data = await redis_client.get(f"driver:stats:{driver_id}")
    
    if data:
        if isinstance(data, bytes):
            data = data.decode('utf-8')
        return json.loads(data)
    
    return None