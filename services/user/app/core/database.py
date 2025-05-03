import asyncpg
import logging
from typing import Any, Dict, List, Optional, AsyncIterator
from asyncpg.pool import Pool
from contextlib import asynccontextmanager

from app.core.config import settings

logger = logging.getLogger(__name__)

# Global connection pool
pool: Optional[Pool] = None

async def init_db() -> None:
    """Initialize the database connection pool and ensure schema is set up."""
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

        # Initialize database schema
        await init_db_schema()

    except Exception as e:
        logger.error(f"Failed to create database connection pool: {e}")
        raise

async def init_db_schema() -> None:
    """Initialize the database schema if it doesn't exist."""
    try:
        logger.info("Checking and initializing database schema")
        conn = await pool.acquire()
        try:
            # Create the uuid-ossp extension if it doesn't exist
            await conn.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";")

            # Try to create the postgis extension if it doesn't exist
            try:
                await conn.execute("CREATE EXTENSION IF NOT EXISTS postgis;")
            except Exception as e:
                logger.warning(f"Could not create PostGIS extension: {e}")
                logger.warning("Continuing without PostGIS support. Some location features might not work.")

            # Create schema for the service
            await conn.execute("CREATE SCHEMA IF NOT EXISTS user_service;")

            # Create users table
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_service.users (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                email VARCHAR(255) UNIQUE NOT NULL,
                phone_number VARCHAR(20) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                first_name VARCHAR(100) NOT NULL,
                last_name VARCHAR(100) NOT NULL,
                date_of_birth DATE,
                profile_picture_url VARCHAR(255),
                is_active BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Create roles table
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_service.roles (
                id SMALLINT PRIMARY KEY,
                name VARCHAR(50) UNIQUE NOT NULL,
                description VARCHAR(255)
            );
            """)

            # Insert default roles
            await conn.execute("""
            INSERT INTO user_service.roles (id, name, description) VALUES
                (1, 'customer', 'Regular customer who orders food'),
                (2, 'restaurant', 'Restaurant owner or manager'),
                (3, 'driver', 'Delivery driver'),
                (4, 'admin', 'System administrator')
            ON CONFLICT (id) DO NOTHING;
            """)

            # Create user_roles table
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_service.user_roles (
                user_id UUID REFERENCES user_service.users(id) ON DELETE CASCADE,
                role_id SMALLINT REFERENCES user_service.roles(id) ON DELETE CASCADE,
                PRIMARY KEY (user_id, role_id)
            );
            """)

            # Try to create addresses table with PostGIS support
            try:
                await conn.execute("""
                CREATE TABLE IF NOT EXISTS user_service.addresses (
                    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                    user_id UUID REFERENCES user_service.users(id) ON DELETE CASCADE,
                    address_line1 VARCHAR(255) NOT NULL,
                    address_line2 VARCHAR(255),
                    city VARCHAR(100) NOT NULL,
                    state VARCHAR(100) NOT NULL,
                    postal_code VARCHAR(20) NOT NULL,
                    country VARCHAR(100) NOT NULL DEFAULT 'Казахстан',
                    latitude DOUBLE PRECISION,
                    longitude DOUBLE PRECISION,
                    is_default BOOLEAN DEFAULT FALSE,
                    address_type VARCHAR(50) NOT NULL,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
                );
                """)

                # Try to add PostGIS column if PostGIS is available
                try:
                    # Check if location column exists
                    location_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_schema = 'user_service'
                        AND table_name = 'addresses'
                        AND column_name = 'location'
                    );
                    """)

                    if not location_exists:
                        await conn.execute("""
                        ALTER TABLE user_service.addresses
                        ADD COLUMN IF NOT EXISTS location GEOGRAPHY(POINT);
                        """)

                        # Create index on addresses.location
                        await conn.execute("""
                        CREATE INDEX IF NOT EXISTS addresses_location_idx ON user_service.addresses USING GIST(location);
                        """)
                except Exception as e:
                    logger.warning(f"Could not add PostGIS location column: {e}")
                    logger.warning("Addresses will use latitude/longitude fields instead of PostGIS.")
            except Exception as e:
                logger.error(f"Failed to create addresses table: {e}")
                raise

            # Create customer_profiles table
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_service.customer_profiles (
                user_id UUID PRIMARY KEY REFERENCES user_service.users(id) ON DELETE CASCADE,
                dietary_preferences JSONB,
                favorite_cuisines JSONB,
                average_rating DECIMAL(3, 2),
                stripe_customer_id VARCHAR(255),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """)

            # Create notification_settings table
            await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_service.notification_settings (
                user_id UUID PRIMARY KEY REFERENCES user_service.users(id) ON DELETE CASCADE,
                email_notifications BOOLEAN DEFAULT TRUE,
                sms_notifications BOOLEAN DEFAULT TRUE,
                push_notifications BOOLEAN DEFAULT TRUE,
                order_updates BOOLEAN DEFAULT TRUE,
                promotional_emails BOOLEAN DEFAULT TRUE,
                new_restaurant_alerts BOOLEAN DEFAULT FALSE,
                special_offers BOOLEAN DEFAULT TRUE,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """)

            logger.info("Database schema initialization completed")
        finally:
            await pool.release(conn)
    except Exception as e:
        logger.error(f"Failed to initialize database schema: {e}")
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

@asynccontextmanager
async def transaction() -> AsyncIterator[asyncpg.Connection]:
    """
    Async contextmanager wrapping a transaction:
      async with transaction() as conn:
          await conn.execute(…)
    """
    if pool is None:
        await init_db()

    conn = await pool.acquire()
    try:
        async with conn.transaction():
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

async def create_transaction():
    """Create a transaction context."""
    if pool is None:
        await init_db()

    # Get a connection first
    conn = await pool.acquire()

    try:
        # Create a transaction on the connection
        tx = conn.transaction()
        await tx.start()

        # Yield an object that can be awaited or used directly
        class TransactionContextManager:
            async def __aenter__(self):
                return tx

            async def __aexit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    await tx.rollback()
                else:
                    await tx.commit()
                await pool.release(conn)

            # These methods allow the object to be awaited directly
            def __await__(self):
                async def _wait():
                    return self
                return _wait().__await__()

        return TransactionContextManager()
    except Exception as e:
        await pool.release(conn)
        raise e
        
@asynccontextmanager
async def create_transaction_context():
    """
    A simpler transaction context manager that can be used with async with.
    
    Example:
    ```
    async with create_transaction_context() as conn:
        await conn.execute("INSERT INTO ...")
        await conn.execute("UPDATE ...")
    ```
    """
    if pool is None:
        await init_db()
        
    conn = await pool.acquire()
    tx = conn.transaction()
    try:
        await tx.start()
        yield conn
        await tx.commit()
    except Exception:
        await tx.rollback()
        raise
    finally:
        await pool.release(conn)
