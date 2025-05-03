import pytest
from datetime import datetime
import uuid
from typing import Dict, Any

from app.workers.analytics_worker import format_order_for_analytics

@pytest.mark.asyncio
async def test_format_order_for_analytics():
    """Test formatting an order for analytics."""
    # Create a test order
    order_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())
    restaurant_id = str(uuid.uuid4())
    driver_id = str(uuid.uuid4())
    
    created_at = datetime.utcnow().isoformat()
    actual_delivery_time = datetime.utcnow().isoformat()
    
    order_data = {
        "id": order_id,
        "customer_id": customer_id,
        "restaurant_id": restaurant_id,
        "driver_id": driver_id,
        "status": "delivered",
        "payment_method": "credit_card",
        "payment_status": "completed",
        "subtotal": 25.0,
        "tax": 2.5,
        "delivery_fee": 5.0,
        "tip": 3.0,
        "promo_discount": 0.0,
        "total_amount": 35.5,
        "restaurant_preparation_time": 20,
        "created_at": created_at,
        "actual_delivery_time": actual_delivery_time,
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
        "food_rating": 4,
        "delivery_rating": 5
    }
    
    # Format order for analytics
    formatted_data = await format_order_for_analytics(order_data)
    
    # Check result
    assert formatted_data is not None
    assert formatted_data["order_id"] == order_id
    assert formatted_data["customer_id"] == customer_id
    assert formatted_data["restaurant_id"] == restaurant_id
    assert formatted_data["driver_id"] == driver_id
    assert formatted_data["status"] == "delivered"
    assert formatted_data["payment_method"] == "credit_card"
    assert formatted_data["payment_status"] == "completed"
    
    # Check metric fields
    assert formatted_data["subtotal"] == 25.0
    assert formatted_data["tax"] == 2.5
    assert formatted_data["delivery_fee"] == 5.0
    assert formatted_data["tip"] == 3.0
    assert formatted_data["promo_discount"] == 0.0
    assert formatted_data["total_amount"] == 35.5
    assert formatted_data["preparation_time_minutes"] == 20
    assert formatted_data["food_rating"] == 4
    assert formatted_data["delivery_rating"] == 5
    assert formatted_data["item_count"] == 2
    
    # Check datetime fields
    assert isinstance(formatted_data["created_at"], int)
    assert isinstance(formatted_data["delivery_time"], int)
    
    # Check computed fields
    assert formatted_data["delivery_time_minutes"] >= 0
    assert formatted_data["total_time_minutes"] >= 0

@pytest.mark.asyncio
async def test_format_order_for_analytics_minimal():
    """Test formatting an order with minimal data for analytics."""
    # Create a test order with minimal data
    order_id = str(uuid.uuid4())
    customer_id = str(uuid.uuid4())
    restaurant_id = str(uuid.uuid4())
    
    created_at = datetime.utcnow().isoformat()
    
    order_data = {
        "id": order_id,
        "customer_id": customer_id,
        "restaurant_id": restaurant_id,
        "status": "placed",
        "payment_method": "credit_card",
        "payment_status": "pending",
        "subtotal": 25.0,
        "tax": 2.5,
        "delivery_fee": 5.0,
        "total_amount": 32.5,
        "created_at": created_at,
        "items": []
    }
    
    # Format order for analytics
    formatted_data = await format_order_for_analytics(order_data)
    
    # Check result
    assert formatted_data is not None
    assert formatted_data["order_id"] == order_id
    assert formatted_data["customer_id"] == customer_id
    assert formatted_data["restaurant_id"] == restaurant_id
    assert formatted_data["status"] == "placed"
    
    # Check metric fields
    assert formatted_data["subtotal"] == 25.0
    assert formatted_data["tax"] == 2.5
    assert formatted_data["delivery_fee"] == 5.0
    assert formatted_data["total_amount"] == 32.5
    assert formatted_data["food_rating"] == 0
    assert formatted_data["delivery_rating"] == 0
    assert formatted_data["item_count"] == 0
    
    # Check datetime fields
    assert isinstance(formatted_data["created_at"], int)
    assert formatted_data["delivery_time"] is None