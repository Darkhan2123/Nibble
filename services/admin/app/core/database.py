import logging
import asyncpg
from typing import Dict, List, Any, Optional, AsyncGenerator
from contextlib import asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

# Connection pool
pool: Optional[asyncpg.Pool] = None

async def init_db() -> None:
    """Initialize the database connection pool and create necessary tables."""
    global pool
    try:
        logger.info("Creating database connection pool")
        pool = await asyncpg.create_pool(
            dsn=settings.DATABASE_URL,
            min_size=5,
            max_size=20
        )
        logger.info("Database connection pool created successfully")
        
        # Initialize admin_service schema and tables
        await init_admin_schema()
    except Exception as e:
        logger.error(f"Failed to create database connection pool: {e}")
        raise

async def init_admin_schema() -> None:
    """Initialize the admin_service schema and tables if they don't exist."""
    logger.info("Initializing admin_service schema and tables")
    async with get_connection() as conn:
        # Create admin_service schema
        await conn.execute("CREATE SCHEMA IF NOT EXISTS admin_service;")
        
        # Create support_tickets table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_service.support_tickets (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL,
            order_id UUID,
            subject VARCHAR(255) NOT NULL,
            description TEXT NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'open',
            priority VARCHAR(50) NOT NULL DEFAULT 'medium',
            assigned_to UUID,
            resolved_at TIMESTAMP WITH TIME ZONE,
            resolution_notes TEXT,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Create ticket_comments table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_service.ticket_comments (
            id UUID PRIMARY KEY,
            ticket_id UUID NOT NULL REFERENCES admin_service.support_tickets(id) ON DELETE CASCADE,
            user_id UUID NOT NULL,
            comment TEXT NOT NULL,
            is_internal BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Create promotions table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_service.promotions (
            id UUID PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            description TEXT,
            promo_code VARCHAR(50) UNIQUE,
            discount_type VARCHAR(20) NOT NULL,
            discount_value DECIMAL(10, 2),
            min_order_amount DECIMAL(10, 2),
            max_discount_amount DECIMAL(10, 2),
            start_date TIMESTAMP WITH TIME ZONE NOT NULL,
            end_date TIMESTAMP WITH TIME ZONE NOT NULL,
            is_active BOOLEAN DEFAULT TRUE,
            usage_limit INTEGER,
            current_usage INTEGER DEFAULT 0,
            applies_to VARCHAR(50)[],
            applies_to_ids UUID[],
            created_by UUID,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """)
        
        # Create user_promotions table
        await conn.execute("""
        CREATE TABLE IF NOT EXISTS admin_service.user_promotions (
            id UUID PRIMARY KEY,
            user_id UUID NOT NULL,
            promotion_id UUID REFERENCES admin_service.promotions(id) ON DELETE CASCADE,
            usage_count INTEGER DEFAULT 0,
            first_used_at TIMESTAMP WITH TIME ZONE,
            last_used_at TIMESTAMP WITH TIME ZONE
        );
        """)
        
        logger.info("Admin service schema and tables initialized successfully")

@asynccontextmanager
async def get_connection():
    """Get a database connection from the pool."""
    global pool
    if pool is None:
        await init_db()
    conn = await pool.acquire()
    try:
        yield conn
    finally:
        await pool.release(conn)

async def get_db() -> AsyncGenerator[asyncpg.Connection, None]:
    """Dependency to get a database connection from the pool."""
    async with get_connection() as conn:
        yield conn

@asynccontextmanager
async def transaction():
    """Transaction context manager."""
    async with get_connection() as conn:
        tx = conn.transaction()
        try:
            await tx.start()
            yield conn
            await tx.commit()
        except Exception:
            await tx.rollback()
            raise

async def fetch_one(query: str, *args) -> Optional[Dict[str, Any]]:
    """Execute a query and return one row as a dictionary."""
    async with get_connection() as conn:
        row = await conn.fetchrow(query, *args)
        if row:
            return dict(row)
        return None

async def fetch_all(query: str, *args) -> List[Dict[str, Any]]:
    """Execute a query and return all rows as dictionaries."""
    async with get_connection() as conn:
        rows = await conn.fetch(query, *args)
        return [dict(row) for row in rows]

async def execute(query: str, *args) -> str:
    """Execute a query and return the status."""
    async with get_connection() as conn:
        return await conn.execute(query, *args)