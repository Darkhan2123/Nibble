import redis.asyncio as redis
import logging
from typing import Optional

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