import logging
import json
from datetime import datetime
from typing import Dict, Any

from app.core.kafka import (
    publish_analytics_event,
    order_topic,
    analytics_topic,
    driver_topic,
    kafka_broker
)

logger = logging.getLogger(__name__)

async def format_order_for_analytics(order_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Formats order data for analytics.
    
    This function takes the raw order data and transforms it into a format
    suitable for Apache Pinot based on the orders schema.
    """
    try:
        # Extract base order fields
        formatted_data = {
            "order_id": order_data.get("id"),
            "customer_id": order_data.get("customer_id"),
            "restaurant_id": order_data.get("restaurant_id"),
            "driver_id": order_data.get("driver_id"),
            "status": order_data.get("status"),
            "payment_method": order_data.get("payment_method"),
            "payment_status": order_data.get("payment_status"),
            "city": None,  # Will be populated from address data
            "state": None,  # Will be populated from address data
            "postal_code": None,  # Will be populated from address data
            "cuisine_type": None,  # Will be populated from restaurant data
            "cancelled_by": order_data.get("cancelled_by"),
            "cancellation_reason": order_data.get("cancellation_reason"),
            
            # Metric fields
            "subtotal": float(order_data.get("subtotal", 0)),
            "tax": float(order_data.get("tax", 0)),
            "delivery_fee": float(order_data.get("delivery_fee", 0)),
            "tip": float(order_data.get("tip", 0)),
            "promo_discount": float(order_data.get("promo_discount", 0)),
            "total_amount": float(order_data.get("total_amount", 0)),
            "preparation_time_minutes": order_data.get("restaurant_preparation_time", 0),
            "delivery_time_minutes": 0,  # Will be calculated
            "total_time_minutes": 0,  # Will be calculated
            "food_rating": None,  # Will be populated if available
            "delivery_rating": None,  # Will be populated if available
            "item_count": len(order_data.get("items", [])),
            
            # DateTime fields
            "created_at": int(datetime.fromisoformat(order_data.get("created_at")).timestamp() * 1000),
            "delivery_time": None  # Will be populated if available
        }
        
        # Calculate delivery time if available
        if order_data.get("actual_delivery_time") and order_data.get("created_at"):
            created_at = datetime.fromisoformat(order_data.get("created_at"))
            delivered_at = datetime.fromisoformat(order_data.get("actual_delivery_time"))
            
            # Set delivery time field
            formatted_data["delivery_time"] = int(delivered_at.timestamp() * 1000)
            
            # Calculate time difference in minutes
            time_diff = (delivered_at - created_at).total_seconds() / 60
            formatted_data["total_time_minutes"] = int(time_diff)
            
            # Estimate delivery time (total time minus preparation time)
            prep_time = formatted_data["preparation_time_minutes"] or 0
            formatted_data["delivery_time_minutes"] = max(0, int(time_diff) - prep_time)
        
        # Clean up any None values for numeric fields
        for field in ["food_rating", "delivery_rating", "preparation_time_minutes", 
                      "delivery_time_minutes", "total_time_minutes"]:
            if formatted_data[field] is None:
                formatted_data[field] = 0
        
        return formatted_data
    
    except Exception as e:
        logger.error(f"Error formatting order for analytics: {e}")
        # Return minimal data to avoid pipeline failures
        return {
            "order_id": order_data.get("id", "unknown"),
            "created_at": int(datetime.now().timestamp() * 1000)
        }

async def publish_order_to_analytics(order_data: Dict[str, Any]) -> None:
    """
    Publishes order data to the analytics topic.
    
    This function formats the order data and publishes it to the analytics
    topic for consumption by the analytics service and Apache Pinot.
    """
    try:
        # Format the order data
        analytics_data = await format_order_for_analytics(order_data)
        
        # Publish to analytics topic
        await publish_analytics_event(
            event_type="order_event",
            data=analytics_data
        )
        
        logger.info(f"Published order {analytics_data['order_id']} to analytics topic")
        
    except Exception as e:
        logger.error(f"Error publishing order to analytics: {e}")

# Event handlers for order lifecycle events
async def handle_order_created(event_data: Dict[str, Any]) -> None:
    """Handler for order created events."""
    data = event_data.get("data", {})
    await publish_order_to_analytics(data)

async def handle_order_updated(event_data: Dict[str, Any]) -> None:
    """Handler for order updated events."""
    data = event_data.get("data", {})
    await publish_order_to_analytics(data)

async def handle_order_delivered(event_data: Dict[str, Any]) -> None:
    """Handler for order delivered events."""
    data = event_data.get("data", {})
    # For delivery events, we want to make sure we have delivery time information
    if "order_id" in data:
        from app.models.order import OrderRepository
        order_repo = OrderRepository()
        order = await order_repo.get_order_by_id(data["order_id"])
        if order:
            await publish_order_to_analytics(order)
    else:
        await publish_order_to_analytics(data)

async def handle_order_cancelled(event_data: Dict[str, Any]) -> None:
    """Handler for order cancelled events."""
    data = event_data.get("data", {})
    # For cancellation events, we want to make sure we have cancellation information
    if "order_id" in data:
        from app.models.order import OrderRepository
        order_repo = OrderRepository()
        order = await order_repo.get_order_by_id(data["order_id"])
        if order:
            await publish_order_to_analytics(order)
    else:
        await publish_order_to_analytics(data)

async def handle_order_rated(event_data: Dict[str, Any]) -> None:
    """Handler for order rated events."""
    data = event_data.get("data", {})
    # For rating events, we want to make sure we have the full order with rating information
    if "order_id" in data:
        from app.models.order import OrderRepository
        order_repo = OrderRepository()
        order = await order_repo.get_order_by_id(data["order_id"])
        if order:
            # Add rating data if not already present
            if "food_rating" not in order and "food_rating" in data:
                order["food_rating"] = data["food_rating"]
            if "delivery_rating" not in order and "delivery_rating" in data:
                order["delivery_rating"] = data["delivery_rating"]
            await publish_order_to_analytics(order)
    else:
        await publish_order_to_analytics(data)

async def setup_analytics_consumers():
    """Setup Kafka consumers for analytics events."""
    # Make sure the broker is initialized
    if not kafka_broker:
        logger.warning("Kafka broker not initialized, skipping analytics consumer setup")
        return
    
    # Register consumers for order events that should be published to analytics
    kafka_broker.subscriber(order_topic("order_created"))(handle_order_created)
    kafka_broker.subscriber(order_topic("order_updated"))(handle_order_updated)
    kafka_broker.subscriber(order_topic("order_status_changed"))(handle_order_updated)
    kafka_broker.subscriber(order_topic("order_cancelled"))(handle_order_cancelled)
    kafka_broker.subscriber(driver_topic("delivery_completed"))(handle_order_delivered)
    
    logger.info("Analytics consumers registered successfully")