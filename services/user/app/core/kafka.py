import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Callable, Awaitable
from faststream.kafka import KafkaBroker
from faststream.kafka.asyncapi import Publisher

from app.core.config import settings

logger = logging.getLogger(__name__)

# Define Kafka topics
TOPICS = {
    "user_events": "user-events",
    "notification_events": "notification-events",
    "order_events": "order-events",
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
    except Exception as e:
        logger.error(f"Failed to create Kafka broker: {e}")
        raise

async def get_kafka_producer():
    """Get a Kafka producer."""
    global kafka_broker
    if kafka_broker is None:
        await init_kafka()
    
    # Return the broker itself for now
    return kafka_broker

async def publish_event(topic: str, key: str, data: Dict[str, Any]) -> None:
    """Simulate publishing an event to Kafka."""
    try:
        # Add metadata to event
        event_data = {
            "event_id": str(uuid.uuid4()),
            "event_time": datetime.utcnow().isoformat(),
            "event_type": key,
            "service": "user-service",
            "data": data
        }
        
        # For now, just log the event
        logger.info(f"[KAFKA-EVENT] {topic}/{key}: {json.dumps(event_data)}")
        
        # Return successful
        return True
    except Exception as e:
        logger.error(f"Failed to publish event to {topic}: {e}")
        # Continue execution even if Kafka fails
        pass

# Example function to publish user created event
async def publish_user_created(user_data: Dict[str, Any]) -> None:
    """Publish a user created event."""
    # Make sure all UUID values are converted to strings
    if "user_id" in user_data and not isinstance(user_data["user_id"], str):
        user_data["user_id"] = str(user_data["user_id"])
        
    await publish_event(
        topic=TOPICS["user_events"],
        key="user_created",
        data=user_data
    )

# Example function to publish user updated event
async def publish_user_updated(user_data: Dict[str, Any]) -> None:
    """Publish a user updated event."""
    # Make sure all UUID values are converted to strings
    if "user_id" in user_data and not isinstance(user_data["user_id"], str):
        user_data["user_id"] = str(user_data["user_id"])
        
    await publish_event(
        topic=TOPICS["user_events"],
        key="user_updated",
        data=user_data
    )

# Example function to publish notification event
async def publish_notification(user_id: str, notification_data: Dict[str, Any]) -> None:
    """Publish a notification event."""
    # Make sure all UUID values are converted to strings
    if not isinstance(user_id, str):
        user_id = str(user_id)
        
    await publish_event(
        topic=TOPICS["notification_events"],
        key="notification_created",
        data={
            "user_id": user_id,
            "notification": notification_data
        }
    )