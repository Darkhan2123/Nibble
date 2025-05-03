import logging
import json
from typing import Dict, Any, Callable, Awaitable
from faststream.kafka import KafkaBroker, KafkaProducer

from app.core.config import settings

logger = logging.getLogger(__name__)

# Define Kafka topics
TOPICS = {
    "order_events": "order-events",
    "payment_events": "payment-events",
    "notification_events": "notification-events",
    "restaurant_events": "restaurant-events",
    "driver_events": "driver-events",
}

# Global Kafka broker
kafka_broker: KafkaBroker = None

async def init_kafka() -> None:
    """Initialize the Kafka broker."""
    global kafka_broker
    try:
        logger.info("Creating Kafka broker")
        kafka_broker = KafkaBroker(settings.KAFKA_BOOTSTRAP_SERVERS)
        logger.info("Kafka broker created successfully")
        
        # Setup notification consumers
        from app.workers.notification_handlers import (
            handle_customer_notification,
            handle_restaurant_notification,
            handle_driver_notification,
            handle_order_status_changed,
            handle_payment_completed,
            handle_payment_failed
        )
        
        # Register consumers
        kafka_broker.subscriber(notification_topic("customer_notification"))(handle_customer_notification)
        kafka_broker.subscriber(notification_topic("restaurant_notification"))(handle_restaurant_notification)
        kafka_broker.subscriber(notification_topic("driver_notification"))(handle_driver_notification)
        kafka_broker.subscriber(order_topic("order_status_changed"))(handle_order_status_changed)
        kafka_broker.subscriber(payment_topic("payment_completed"))(handle_payment_completed)
        kafka_broker.subscriber(payment_topic("payment_failed"))(handle_payment_failed)
        
        # Start consumers
        await kafka_broker.start()
        
    except Exception as e:
        logger.error(f"Failed to create Kafka broker: {e}")
        raise

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