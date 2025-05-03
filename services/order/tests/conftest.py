import pytest
import asyncio
from httpx import AsyncClient
from fastapi import FastAPI
from typing import Dict, Any, Generator, AsyncGenerator
import uuid
import json
from datetime import datetime

from app.main import app
from app.core.database import get_connection
from app.models.order import OrderRepository
from app.models.cart import CartRepository
from app.models.payment import PaymentRepository
from app.core.redis import update_cart, get_redis_client

# Fixtures for test database setup
@pytest.fixture
async def test_db():
    """Setup and teardown test database for each test."""
    # This would normally setup a test database and tables
    # For simplicity, we'll just use a transaction that gets rolled back
    async with get_connection() as conn:
        tx = conn.transaction()
        await tx.start()
        
        try:
            yield conn
        finally:
            await tx.rollback()

# Fixtures for HTTP client testing
@pytest.fixture
async def async_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

# Fixture for mock authentication
@pytest.fixture
def mock_auth_headers() -> Dict[str, str]:
    """Return mock auth headers for testing endpoints."""
    return {
        "Authorization": "Bearer mock_token"
    }

# Customer user fixture
@pytest.fixture
def customer_user() -> Dict[str, Any]:
    """Return a mock customer user."""
    return {
        "id": str(uuid.uuid4()),
        "email": "customer@example.com",
        "role": "customer"
    }

# Restaurant user fixture
@pytest.fixture
def restaurant_user() -> Dict[str, Any]:
    """Return a mock restaurant user."""
    return {
        "id": str(uuid.uuid4()),
        "email": "restaurant@example.com",
        "role": "restaurant"
    }

# Driver user fixture
@pytest.fixture
def driver_user() -> Dict[str, Any]:
    """Return a mock driver user."""
    return {
        "id": str(uuid.uuid4()),
        "email": "driver@example.com",
        "role": "driver"
    }

# Admin user fixture
@pytest.fixture
def admin_user() -> Dict[str, Any]:
    """Return a mock admin user."""
    return {
        "id": str(uuid.uuid4()),
        "email": "admin@example.com",
        "role": "admin"
    }

# Mock cart data fixture
@pytest.fixture
async def mock_cart(customer_user):
    """Create a mock cart in Redis."""
    user_id = customer_user["id"]
    restaurant_id = str(uuid.uuid4())
    
    cart_data = {
        "restaurant_id": restaurant_id,
        "items": [
            {
                "menu_item_id": str(uuid.uuid4()),
                "menu_item_name": "Test Item 1",
                "quantity": 2,
                "unit_price": 10.0,
                "subtotal": 20.0
            },
            {
                "menu_item_id": str(uuid.uuid4()),
                "menu_item_name": "Test Item 2",
                "quantity": 1,
                "unit_price": 5.0,
                "subtotal": 5.0
            }
        ],
        "subtotal": 25.0,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    await update_cart(user_id, cart_data)
    
    yield cart_data
    
    # Cleanup - delete the cart
    redis_client = await get_redis_client()
    await redis_client.delete(f"cart:{user_id}")

# Mock order data fixture
@pytest.fixture
async def mock_order(customer_user, restaurant_user, test_db):
    """Create a mock order in the database."""
    order_repo = OrderRepository()
    
    # Create a mock order
    order_data = {
        "customer_id": customer_user["id"],
        "restaurant_id": restaurant_user["id"],
        "address_id": str(uuid.uuid4()),
        "items": [
            {
                "menu_item_id": str(uuid.uuid4()),
                "menu_item_name": "Test Item 1",
                "quantity": 2,
                "unit_price": 10.0
            },
            {
                "menu_item_id": str(uuid.uuid4()),
                "menu_item_name": "Test Item 2",
                "quantity": 1,
                "unit_price": 5.0
            }
        ],
        "subtotal": 25.0,
        "delivery_fee": 5.0,
        "payment_method": "credit_card",
        "special_instructions": "Test instructions"
    }
    
    # Create the order
    order = await order_repo.create_order(**order_data)
    
    yield order