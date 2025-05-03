import pytest
from httpx import AsyncClient
import json
from typing import Dict, Any

# Mock auth middleware to bypass authentication
@pytest.fixture(autouse=True)
def mock_auth(monkeypatch, customer_user):
    """Override the authentication dependencies for testing."""
    async def mock_get_current_user():
        return customer_user
    
    async def mock_get_current_restaurant():
        return customer_user
    
    async def mock_get_current_driver():
        return customer_user
    
    async def mock_get_current_admin():
        return customer_user
    
    # Apply the monkeypatches
    from app.api.v1.endpoints import orders
    monkeypatch.setattr(orders, "get_current_user", mock_get_current_user)
    monkeypatch.setattr(orders, "get_current_restaurant", mock_get_current_restaurant)
    monkeypatch.setattr(orders, "get_current_driver", mock_get_current_driver)
    monkeypatch.setattr(orders, "get_current_admin", mock_get_current_admin)

# Test create order endpoint
@pytest.mark.asyncio
async def test_create_order(async_client: AsyncClient, mock_auth_headers, customer_user, mock_cart):
    """Test creating a new order."""
    # Create order request data
    request_data = {
        "restaurant_id": mock_cart["restaurant_id"],
        "address_id": "00000000-0000-0000-0000-000000000001",
        "items": [
            {
                "menu_item_id": item["menu_item_id"],
                "menu_item_name": item["menu_item_name"],
                "quantity": item["quantity"],
                "unit_price": item["unit_price"]
            }
            for item in mock_cart["items"]
        ],
        "subtotal": mock_cart["subtotal"],
        "delivery_fee": 5.0,
        "payment_method": "credit_card",
        "special_instructions": "Test instructions"
    }
    
    # Send request
    response = await async_client.post(
        "/api/v1/orders",
        json=request_data,
        headers=mock_auth_headers
    )
    
    # Check response
    assert response.status_code == 201
    response_data = response.json()
    assert "id" in response_data
    assert response_data["customer_id"] == customer_user["id"]
    assert response_data["restaurant_id"] == mock_cart["restaurant_id"]
    assert response_data["subtotal"] == mock_cart["subtotal"]
    assert response_data["status"] == "placed"
    assert response_data["payment_status"] == "pending"

# Test get order by ID endpoint
@pytest.mark.asyncio
async def test_get_order_by_id(async_client: AsyncClient, mock_auth_headers, mock_order):
    """Test getting an order by ID."""
    # Send request
    response = await async_client.get(
        f"/api/v1/orders/{mock_order['id']}",
        headers=mock_auth_headers
    )
    
    # Check response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == mock_order["id"]
    assert response_data["customer_id"] == mock_order["customer_id"]
    assert response_data["restaurant_id"] == mock_order["restaurant_id"]
    assert response_data["status"] == mock_order["status"]

# Test get orders for current customer
@pytest.mark.asyncio
async def test_get_customer_orders(async_client: AsyncClient, mock_auth_headers, customer_user, mock_order):
    """Test getting orders for the current customer."""
    # Send request
    response = await async_client.get(
        "/api/v1/orders/customer/me",
        headers=mock_auth_headers
    )
    
    # Check response
    assert response.status_code == 200
    response_data = response.json()
    assert "orders" in response_data
    assert isinstance(response_data["orders"], list)
    assert len(response_data["orders"]) > 0
    
    # Check that the mock order is in the response
    order_ids = [order["id"] for order in response_data["orders"]]
    assert mock_order["id"] in order_ids

# Test update order status
@pytest.mark.asyncio
async def test_update_order_status(async_client: AsyncClient, mock_auth_headers, mock_order):
    """Test updating an order's status."""
    # Create update request data
    request_data = {
        "status": "confirmed",
        "notes": "Order confirmed by restaurant"
    }
    
    # Send request
    response = await async_client.put(
        f"/api/v1/orders/{mock_order['id']}/status",
        json=request_data,
        headers=mock_auth_headers
    )
    
    # Check response
    assert response.status_code == 200
    response_data = response.json()
    assert response_data["id"] == mock_order["id"]
    assert response_data["status"] == "confirmed"