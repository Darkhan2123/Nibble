import pytest
import uuid
from datetime import datetime
from app.models.order import OrderRepository

@pytest.mark.asyncio
async def test_create_order(test_db):
    """Test creating a new order."""
    order_repo = OrderRepository()
    
    # Test data
    customer_id = str(uuid.uuid4())
    restaurant_id = str(uuid.uuid4())
    address_id = str(uuid.uuid4())
    
    items = [
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
    ]
    
    subtotal = 25.0
    delivery_fee = 5.0
    payment_method = "credit_card"
    special_instructions = "Test instructions"
    
    # Create order
    order = await order_repo.create_order(
        customer_id=customer_id,
        restaurant_id=restaurant_id,
        address_id=address_id,
        items=items,
        subtotal=subtotal,
        delivery_fee=delivery_fee,
        payment_method=payment_method,
        special_instructions=special_instructions
    )
    
    # Check result
    assert order is not None
    assert "id" in order
    assert order["customer_id"] == customer_id
    assert order["restaurant_id"] == restaurant_id
    assert order["status"] == "placed"
    assert order["payment_status"] == "pending"
    assert order["subtotal"] == subtotal
    assert order["delivery_fee"] == delivery_fee
    assert order["total_amount"] == subtotal + order["tax"] + delivery_fee
    assert "items" in order
    assert len(order["items"]) == 2

@pytest.mark.asyncio
async def test_get_order_by_id(test_db):
    """Test retrieving an order by ID."""
    order_repo = OrderRepository()
    
    # First create a test order
    customer_id = str(uuid.uuid4())
    restaurant_id = str(uuid.uuid4())
    address_id = str(uuid.uuid4())
    
    items = [
        {
            "menu_item_id": str(uuid.uuid4()),
            "menu_item_name": "Test Item",
            "quantity": 1,
            "unit_price": 10.0
        }
    ]
    
    created_order = await order_repo.create_order(
        customer_id=customer_id,
        restaurant_id=restaurant_id,
        address_id=address_id,
        items=items,
        subtotal=10.0,
        delivery_fee=5.0,
        payment_method="credit_card"
    )
    
    # Retrieve order
    order = await order_repo.get_order_by_id(created_order["id"])
    
    # Check result
    assert order is not None
    assert order["id"] == created_order["id"]
    assert order["customer_id"] == customer_id
    assert order["restaurant_id"] == restaurant_id
    assert order["status"] == "placed"

@pytest.mark.asyncio
async def test_update_order_status(test_db):
    """Test updating an order's status."""
    order_repo = OrderRepository()
    
    # First create a test order
    customer_id = str(uuid.uuid4())
    restaurant_id = str(uuid.uuid4())
    address_id = str(uuid.uuid4())
    
    items = [
        {
            "menu_item_id": str(uuid.uuid4()),
            "menu_item_name": "Test Item",
            "quantity": 1,
            "unit_price": 10.0
        }
    ]
    
    created_order = await order_repo.create_order(
        customer_id=customer_id,
        restaurant_id=restaurant_id,
        address_id=address_id,
        items=items,
        subtotal=10.0,
        delivery_fee=5.0,
        payment_method="credit_card"
    )
    
    # Update status
    updated_order = await order_repo.update_order_status(
        order_id=created_order["id"],
        status="confirmed",
        updated_by=restaurant_id,
        notes="Order confirmed by restaurant"
    )
    
    # Check result
    assert updated_order is not None
    assert updated_order["id"] == created_order["id"]
    assert updated_order["status"] == "confirmed"
    
    # Check status history
    history = await order_repo.get_order_status_history(created_order["id"])
    assert len(history) == 2  # Initial "placed" status + new "confirmed" status
    assert history[0]["status"] == "placed"
    assert history[1]["status"] == "confirmed"
    assert history[1]["updated_by_user_id"] == restaurant_id
    assert history[1]["notes"] == "Order confirmed by restaurant"