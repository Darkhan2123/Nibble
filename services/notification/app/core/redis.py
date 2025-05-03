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

# Notification storage
async def store_notification(
    user_id: str,
    title: str,
    message: str,
    notification_type: str,
    reference_id: Optional[str] = None,
    reference_type: Optional[str] = None
) -> Dict[str, Any]:
    """Store a notification in Redis."""
    redis_client = await get_redis_client()
    
    notification_id = f"notif:{datetime.utcnow().timestamp():.6f}:{user_id}"
    
    notification_data = {
        "id": notification_id,
        "user_id": user_id,
        "title": title,
        "message": message,
        "type": notification_type,
        "reference_id": reference_id,
        "reference_type": reference_type,
        "is_read": False,
        "created_at": datetime.utcnow().isoformat()
    }
    
    # Store notification
    await redis_client.set(
        f"notification:{notification_id}",
        json.dumps(notification_data),
        ex=604800  # 7 days expiry
    )
    
    # Add to user's notifications list
    await redis_client.zadd(
        f"user:notifications:{user_id}",
        {notification_id: datetime.utcnow().timestamp()}
    )
    
    # Trim list to 100 recent notifications
    await redis_client.zremrangebyrank(
        f"user:notifications:{user_id}",
        0,
        -101
    )
    
    return notification_data

async def get_user_notifications(
    user_id: str,
    limit: int = 20,
    offset: int = 0
) -> List[Dict[str, Any]]:
    """Get a user's notifications."""
    redis_client = await get_redis_client()
    
    # Get notification IDs from sorted set, newest first
    notification_ids = await redis_client.zrevrange(
        f"user:notifications:{user_id}",
        offset,
        offset + limit - 1
    )
    
    # Get notification data
    notifications = []
    for notif_id in notification_ids:
        notif_id_str = notif_id.decode("utf-8")
        notif_data = await redis_client.get(f"notification:{notif_id_str}")
        
        if notif_data:
            notifications.append(json.loads(notif_data))
    
    return notifications

async def mark_notification_as_read(
    notification_id: str,
    user_id: str
) -> bool:
    """Mark a notification as read."""
    redis_client = await get_redis_client()
    
    # Get notification data
    notif_data_raw = await redis_client.get(f"notification:{notification_id}")
    
    if not notif_data_raw:
        return False
    
    notif_data = json.loads(notif_data_raw)
    
    # Check ownership
    if notif_data.get("user_id") != user_id:
        return False
    
    # Update read status
    notif_data["is_read"] = True
    
    # Save back to Redis
    await redis_client.set(
        f"notification:{notification_id}",
        json.dumps(notif_data),
        keepttl=True
    )
    
    return True

async def mark_all_notifications_as_read(user_id: str) -> int:
    """Mark all of a user's notifications as read."""
    redis_client = await get_redis_client()
    
    # Get all notification IDs
    notification_ids = await redis_client.zrange(
        f"user:notifications:{user_id}",
        0,
        -1
    )
    
    count = 0
    
    # Update each notification
    for notif_id in notification_ids:
        notif_id_str = notif_id.decode("utf-8")
        notif_data_raw = await redis_client.get(f"notification:{notif_id_str}")
        
        if notif_data_raw:
            notif_data = json.loads(notif_data_raw)
            
            if not notif_data.get("is_read"):
                notif_data["is_read"] = True
                
                # Save back to Redis
                await redis_client.set(
                    f"notification:{notif_id_str}",
                    json.dumps(notif_data),
                    keepttl=True
                )
                
                count += 1
    
    return count