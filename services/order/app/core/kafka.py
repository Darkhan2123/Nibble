import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Callable, Awaitable
from faststream.kafka import KafkaBroker

from app.core.config import settings

logger = logging.getLogger(__name__)

TOPICS = {
    "order_events": "order-events",
    "payment_events": "payment-events",
    "notification_events": "notification-events",
    "restaurant_events": "restaurant-events",
    "driver_events": "driver-events",
    "analytics_events": "analytics-events",
}

# Global Kafka broker
kafka_broker: KafkaBroker = None
kafka_consumer = None

async def init_kafka() -> None:
    """Initialize the Kafka broker."""
    global kafka_broker
    try:
        logger.info("Creating Kafka broker")
        kafka_broker = KafkaBroker(settings.KAFKA_BOOTSTRAP_SERVERS)
        logger.info("Kafka broker created successfully")

        # Skip consumer setup for initial testing to avoid dependency issues
        # We'll focus on getting the basic services running first
        logger.info("Skipping Kafka consumer setup for initial testing")

        # Comment out consumer setup to simplify for now
        """
        # Setup consumers
        from app.workers.order_processors import (
            handle_payment_completed,
            handle_payment_failed,
            handle_restaurant_status_changed,
            handle_driver_location_updated,
            handle_delivery_completed
        )

        # Register consumers
        kafka_broker.subscriber(payment_topic("payment_completed"))(handle_payment_completed)
        kafka_broker.subscriber(payment_topic("payment_failed"))(handle_payment_failed)
        kafka_broker.subscriber(restaurant_topic("restaurant_status_changed"))(handle_restaurant_status_changed)
        kafka_broker.subscriber(driver_topic("driver_location_updated"))(handle_driver_location_updated)
        kafka_broker.subscriber(driver_topic("delivery_completed"))(handle_delivery_completed)

        # Setup analytics consumers
        from app.workers.analytics_worker import setup_analytics_consumers
        await setup_analytics_consumers()

        # Start consumers
        await kafka_broker.start()
        """

    except Exception as e:
        logger.error(f"Failed to create Kafka broker: {e}")
        # Log error but continue so we can test other parts of the service
        logger.warning(f"Continuing without Kafka for initial testing")
        return None

async def get_kafka_producer():
    """Get a Kafka producer."""
    global kafka_broker
    if kafka_broker is None:
        await init_kafka()

    return kafka_broker

async def publish_event(topic: str, key: str, data: Dict[str, Any]) -> None:
    """Publish an event to Kafka."""
    try:
        broker = await get_kafka_producer()

        # Add metadata to event
        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_time": datetime.utcnow().isoformat(),
            "event_type": key,
            "service": "order-service",
            "data": data
        }

        try:
            # Try with the broker.publish method
            await broker.publish(
                message=json.dumps(event_data).encode(),
                topic=topic,
                key=key.encode(),
            )
        except (AttributeError, TypeError) as e:
            # Fallback to older API if needed
            logger.debug(f"Falling back to older Kafka API: {str(e)}")
            try:
                # Try to get producer if broker.publish is not available
                producer = getattr(broker, "get_producer", lambda: broker)()
                send_method = getattr(producer, "send", None)
                if send_method:
                    await send_method(
                        topic=topic,
                        key=key.encode(),
                        value=json.dumps(event_data).encode()
                    )
                else:
                    logger.warning("Could not find a working method to publish to Kafka")
            except Exception as inner_e:
                logger.error(f"Fallback publishing failed: {str(inner_e)}")
                # Just log for now so we can proceed with testing other services

        logger.debug(f"Published event to {topic} with key {key}")
    except Exception as e:
        logger.error(f"Failed to publish event to {topic}: {str(e)}")
        # Continue execution even if Kafka fails
        pass

# Helper functions to get topic names
def order_topic(event_type: str) -> str:
    """Get the topic name for order events."""
    return TOPICS["order_events"]

def payment_topic(event_type: str) -> str:
    """Get the topic name for payment events."""
    return TOPICS["payment_events"]

def notification_topic(event_type: str) -> str:
    """Get the topic name for notification events."""
    return TOPICS["notification_events"]

def restaurant_topic(event_type: str) -> str:
    """Get the topic name for restaurant events."""
    return TOPICS["restaurant_events"]

def driver_topic(event_type: str) -> str:
    """Get the topic name for driver events."""
    return TOPICS["driver_events"]

def analytics_topic(event_type: str) -> str:
    """Get the topic name for analytics events."""
    return TOPICS["analytics_events"]

# Order-specific events
async def publish_order_created(order_data: Dict[str, Any]) -> None:
    """Publish an order created event."""
    await publish_event(
        topic=order_topic("order_created"),
        key="order_created",
        data=order_data
    )

async def publish_order_updated(order_data: Dict[str, Any]) -> None:
    """Publish an order updated event."""
    await publish_event(
        topic=order_topic("order_updated"),
        key="order_updated",
        data=order_data
    )

async def publish_order_status_changed(order_id: str, status: str) -> None:
    """Publish an order status changed event."""
    await publish_event(
        topic=order_topic("order_status_changed"),
        key="order_status_changed",
        data={
            "order_id": order_id,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def publish_order_cancelled(order_id: str, reason: str) -> None:
    """Publish an order cancelled event."""
    await publish_event(
        topic=order_topic("order_cancelled"),
        key="order_cancelled",
        data={
            "order_id": order_id,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Payment-specific events
async def publish_payment_created(payment_data: Dict[str, Any]) -> None:
    """Publish a payment created event."""
    await publish_event(
        topic=payment_topic("payment_created"),
        key="payment_created",
        data=payment_data
    )

async def publish_payment_success(payment_data: Dict[str, Any]) -> None:
    """Publish a payment success event."""
    await publish_event(
        topic=payment_topic("payment_completed"),
        key="payment_completed",
        data=payment_data
    )

async def publish_payment_failed(payment_data: Dict[str, Any]) -> None:
    """Publish a payment failed event."""
    await publish_event(
        topic=payment_topic("payment_failed"),
        key="payment_failed",
        data=payment_data
    )

# Notification events
async def publish_customer_notification(user_id: str, message: str, notification_type: str) -> None:
    """Publish a customer notification event."""
    await publish_event(
        topic=notification_topic("customer_notification"),
        key="customer_notification",
        data={
            "user_id": user_id,
            "message": message,
            "type": notification_type,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def publish_restaurant_notification(restaurant_id: str, message: str, notification_type: str) -> None:
    """Publish a restaurant notification event."""
    await publish_event(
        topic=notification_topic("restaurant_notification"),
        key="restaurant_notification",
        data={
            "restaurant_id": restaurant_id,
            "message": message,
            "type": notification_type,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def publish_driver_notification(driver_id: str, message: str, notification_type: str) -> None:
    """Publish a driver notification event."""
    await publish_event(
        topic=notification_topic("driver_notification"),
        key="driver_notification",
        data={
            "driver_id": driver_id,
            "message": message,
            "type": notification_type,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

# Analytics events
async def publish_analytics_event(event_type: str, data: Dict[str, Any]) -> None:
    """Publish an analytics event."""
    await publish_event(
        topic=analytics_topic(event_type),
        key=event_type,
        data=data
    )
