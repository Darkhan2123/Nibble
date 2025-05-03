import asyncpg
import logging
from typing import Any, Dict, List, Optional
from asyncpg.pool import Pool
from contextlib import asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global connection pool
pool: Optional[Pool] = None

async def init_db() -> None:
    """Initialize the database connection pool."""
    global pool
    try:
        logger.info("Creating database connection pool")
        pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=settings.DB_MIN_POOL_SIZE,
            max_size=settings.DB_MAX_POOL_SIZE,
            max_inactive_connection_lifetime=settings.DB_MAX_INACTIVE_CONN_LIFETIME,
            command_timeout=60,
        )
        logger.info("Database connection pool created successfully")
    except Exception as e:
        logger.error(f"Failed to create database connection pool: {e}")
        raise

@asynccontextmanager
async def get_connection():
    """Get a connection from the pool."""
    if pool is None:
        await init_db()
    
    conn = await pool.acquire()
    try:
        yield conn
    finally:
        await pool.release(conn)

async def get_db():
    """Dependency to get a database connection."""
    async with get_connection() as conn:
        yield conn

async def execute_query(query: str, *args, fetch: bool = False) -> List[Dict[str, Any]]:
    """Execute a SQL query and optionally fetch results."""
    async with get_connection() as conn:
        try:
            if fetch:
                result = await conn.fetch(query, *args)
                return [dict(row) for row in result]
            else:
                return await conn.execute(query, *args)
        except Exception as e:
            logger.error(f"Database query error: {e}, Query: {query}")
            raise

async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Fetch a single row from the database."""
    async with get_connection() as conn:
        try:
            result = await conn.fetchrow(query, *args)
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Database query error: {e}, Query: {query}")
            raise

async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """Fetch all rows from the database."""
    return await execute_query(query, *args, fetch=True)

async def execute(query: str, *args) -> str:
    """Execute a query without returning results."""
    return await execute_query(query, *args, fetch=False)

async def transaction():
    """Create a transaction context."""
    if pool is None:
        await init_db()
    
    return pool.transaction()