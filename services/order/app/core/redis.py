import redis.asyncio as redis
import logging
import json
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

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

# Order cart management
async def get_cart(user_id: str) -> Optional[Dict[str, Any]]:
    """Get a user's shopping cart."""
    redis_client = await get_redis_client()
    
    cart_data = await redis_client.get(f"cart:{user_id}")
    
    if cart_data:
        return json.loads(cart_data)
    
    return None

async def update_cart(user_id: str, cart: Dict[str, Any], ttl: int = 86400) -> bool:
    """Update or create a user's shopping cart."""
    redis_client = await get_redis_client()
    
    # Add timestamp if not present
    if "updated_at" not in cart:
        cart["updated_at"] = datetime.utcnow().isoformat()
    
    # Set cart with expiration
    await redis_client.setex(
        f"cart:{user_id}",
        ttl,
        json.dumps(cart)
    )
    
    return True

async def delete_cart(user_id: str) -> bool:
    """Delete a user's shopping cart."""
    redis_client = await get_redis_client()
    
    result = await redis_client.delete(f"cart:{user_id}")
    
    return result > 0

# Order status tracking
async def update_order_status(order_id: str, status: str, data: Dict[str, Any] = None) -> bool:
    """Update an order's status in Redis for real-time tracking."""
    redis_client = await get_redis_client()
    
    status_data = {
        "status": status,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    if data:
        status_data.update(data)
    
    # Set a reasonable TTL for order status (24 hours)
    await redis_client.setex(
        f"order:status:{order_id}",
        86400,
        json.dumps(status_data)
    )
    
    return True

async def get_order_status(order_id: str) -> Optional[Dict[str, Any]]:
    """Get an order's current status from Redis."""
    redis_client = await get_redis_client()
    
    status_data = await redis_client.get(f"order:status:{order_id}")
    
    if status_data:
        return json.loads(status_data)
    
    return None

# Payment tracking
async def create_payment_intent(order_id: str, payment_intent_id: str, amount: float, ttl: int = 1800) -> bool:
    """Store a payment intent in Redis with expiration."""
    redis_client = await get_redis_client()
    
    payment_data = {
        "payment_intent_id": payment_intent_id,
        "order_id": order_id,
        "amount": amount,
        "status": "created",
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Set with expiration (default 30 minutes)
    await redis_client.setex(
        f"payment:intent:{payment_intent_id}",
        ttl,
        json.dumps(payment_data)
    )
    
    # Also index by order ID
    await redis_client.setex(
        f"payment:order:{order_id}",
        ttl,
        json.dumps(payment_data)
    )
    
    return True

async def update_payment_status(payment_intent_id: str, status: str, metadata: Dict[str, Any] = None) -> bool:
    """Update a payment intent's status in Redis."""
    redis_client = await get_redis_client()
    
    # Get existing payment data
    payment_data_json = await redis_client.get(f"payment:intent:{payment_intent_id}")
    
    if not payment_data_json:
        logger.error(f"Payment intent {payment_intent_id} not found in Redis")
        return False
    
    payment_data = json.loads(payment_data_json)
    order_id = payment_data.get("order_id")
    
    # Update status
    payment_data["status"] = status
    payment_data["updated_at"] = datetime.utcnow().isoformat()
    
    if metadata:
        payment_data["metadata"] = metadata
    
    # Update by payment intent ID
    await redis_client.setex(
        f"payment:intent:{payment_intent_id}",
        1800,  # Preserve 30 minute TTL
        json.dumps(payment_data)
    )
    
    # Update by order ID
    if order_id:
        await redis_client.setex(
            f"payment:order:{order_id}",
            1800,  # Preserve 30 minute TTL
            json.dumps(payment_data)
        )
    
    return True

async def get_payment_by_intent_id(payment_intent_id: str) -> Optional[Dict[str, Any]]:
    """Get payment data by payment intent ID."""
    redis_client = await get_redis_client()
    
    payment_data = await redis_client.get(f"payment:intent:{payment_intent_id}")
    
    if payment_data:
        return json.loads(payment_data)
    
    return None

async def get_payment_by_order_id(order_id: str) -> Optional[Dict[str, Any]]:
    """Get payment data by order ID."""
    redis_client = await get_redis_client()
    
    payment_data = await redis_client.get(f"payment:order:{order_id}")
    
    if payment_data:
        return json.loads(payment_data)
    
    return None

# Order processing queue
async def add_to_processing_queue(order_id: str, data: Dict[str, Any]) -> bool:
    """Add an order to the processing queue."""
    redis_client = await get_redis_client()
    
    queue_data = {
        "order_id": order_id,
        "status": "queued",
        "queued_at": datetime.utcnow().isoformat(),
        **data
    }
    
    # Add to sorted set with current timestamp as score
    timestamp = datetime.utcnow().timestamp()
    await redis_client.zadd(
        "order:processing:queue",
        {order_id: timestamp}
    )
    
    # Store order data
    await redis_client.set(
        f"order:processing:data:{order_id}",
        json.dumps(queue_data)
    )
    
    return True

async def get_next_order_from_queue() -> Optional[str]:
    """Get the next order ID from the processing queue."""
    redis_client = await get_redis_client()
    
    # Get the oldest item from the queue (lowest score)
    result = await redis_client.zrange("order:processing:queue", 0, 0)
    
    if result:
        return result[0].decode("utf-8")
    
    return None

async def remove_from_processing_queue(order_id: str) -> bool:
    """Remove an order from the processing queue."""
    redis_client = await get_redis_client()
    
    # Remove from sorted set
    removed = await redis_client.zrem("order:processing:queue", order_id)
    
    # Remove order data
    await redis_client.delete(f"order:processing:data:{order_id}")
    
    return removed > 0

async def get_processing_order_data(order_id: str) -> Optional[Dict[str, Any]]:
    """Get data for an order in the processing queue."""
    redis_client = await get_redis_client()
    
    data = await redis_client.get(f"order:processing:data:{order_id}")
    
    if data:
        return json.loads(data)
    
    return None

# Real-time order tracking functions
async def update_order_tracking_data(order_id: str, data: Dict[str, Any], ttl: int = 86400) -> bool:
    """Update real-time tracking data for an order."""
    redis_client = await get_redis_client()
    
    # Add timestamp if not present
    if "last_updated" not in data:
        data["last_updated"] = datetime.utcnow().isoformat()
    
    # Set tracking data with expiration
    await redis_client.setex(
        f"order:tracking:{order_id}",
        ttl,
        json.dumps(data)
    )
    
    return True

async def get_order_tracking_data(order_id: str) -> Optional[Dict[str, Any]]:
    """Get real-time tracking data for an order."""
    redis_client = await get_redis_client()
    
    data = await redis_client.get(f"order:tracking:{order_id}")
    
    if data:
        return json.loads(data)
    
    return None
    
async def update_driver_location_for_order(order_id: str, latitude: float, longitude: float) -> bool:
    """Update driver location for an order."""
    redis_client = await get_redis_client()
    
    # Get existing tracking data
    tracking_data_json = await redis_client.get(f"order:tracking:{order_id}")
    
    if not tracking_data_json:
        # If no tracking data exists, create with minimal data
        tracking_data = {
            "driver_location": {
                "latitude": latitude,
                "longitude": longitude
            },
            "last_location_update": datetime.utcnow().isoformat()
        }
    else:
        tracking_data = json.loads(tracking_data_json)
        tracking_data["driver_location"] = {
            "latitude": latitude,
            "longitude": longitude
        }
        tracking_data["last_location_update"] = datetime.utcnow().isoformat()
    
    # Set tracking data with expiration (24 hours)
    await redis_client.setex(
        f"order:tracking:{order_id}",
        86400,
        json.dumps(tracking_data)
    )
    
    # Also store in a time-series-like structure for path history
    current_time = datetime.utcnow().isoformat()
    location_point = {
        "latitude": latitude,
        "longitude": longitude,
        "timestamp": current_time
    }
    
    # Add to the list using RPUSH (right push)
    await redis_client.rpush(
        f"order:tracking:path:{order_id}",
        json.dumps(location_point)
    )
    
    # Set expiration on the path list if not already set
    if not await redis_client.ttl(f"order:tracking:path:{order_id}"):
        await redis_client.expire(f"order:tracking:path:{order_id}", 86400)  # 24 hours
    
    return True

async def get_driver_path_for_order(order_id: str, limit: int = 100) -> List[Dict[str, Any]]:
    """Get the path history of driver locations for an order."""
    redis_client = await get_redis_client()
    
    # Get the full list
    path_data = await redis_client.lrange(f"order:tracking:path:{order_id}", 0, -1)
    
    # Parse and return as list of dicts
    path = []
    for point_json in path_data:
        path.append(json.loads(point_json))
    
    # Limit the results if necessary
    if len(path) > limit:
        path = path[-limit:]  # Return only the most recent points
    
    return path