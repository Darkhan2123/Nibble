import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Callable, Awaitable
from faststream.kafka import KafkaBroker  # KafkaProducer is no longer available in this version
from typing import Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# Define Kafka topics
TOPICS = {
    "restaurant_events": "restaurant-events",
    "menu_events": "menu-events",
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

async def get_kafka_producer() -> Any:
    """Get a Kafka producer."""
    global kafka_broker
    if kafka_broker is None:
        await init_kafka()
    
    # In newer versions of faststream, we use the broker directly
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
            "service": "restaurant-service",
            "data": data
        }
        
        # Modern faststream API uses publish method directly on broker
        try:
            # Try with the broker.publish method
            await broker.publish(
                message=json.dumps(event_data).encode(),
                topic=topic,
                key=key.encode(),
            )
        except AttributeError:
            # Fallback to older API if needed
            logger.debug("Falling back to older Kafka API")
            producer = getattr(broker, "get_producer", lambda: broker)()
            send_method = getattr(producer, "send", None)
            if send_method:
                await send_method(
                    topic=topic,
                    key=key.encode(),
                    value=json.dumps(event_data).encode()
                )
            else:
                logger.error("Could not find a working method to publish to Kafka")
        
        logger.debug(f"Published event to {topic} with key {key}")
    except Exception as e:
        logger.error(f"Failed to publish event to {topic}: {e}")
        # Continue execution even if Kafka fails
        pass

# Restaurant-specific events
async def publish_restaurant_created(restaurant_data: Dict[str, Any]) -> None:
    """Publish a restaurant created event."""
    await publish_event(
        topic=TOPICS["restaurant_events"],
        key="restaurant_created",
        data=restaurant_data
    )

async def publish_restaurant_updated(restaurant_data: Dict[str, Any]) -> None:
    """Publish a restaurant updated event."""
    await publish_event(
        topic=TOPICS["restaurant_events"],
        key="restaurant_updated",
        data=restaurant_data
    )

async def publish_restaurant_status_changed(restaurant_id: str, is_active: bool) -> None:
    """Publish a restaurant status changed event."""
    await publish_event(
        topic=TOPICS["restaurant_events"],
        key="restaurant_status_changed",
        data={
            "restaurant_id": restaurant_id,
            "is_active": is_active
        }
    )

# Menu-specific events
async def publish_menu_item_created(menu_item_data: Dict[str, Any]) -> None:
    """Publish a menu item created event."""
    await publish_event(
        topic=TOPICS["menu_events"],
        key="menu_item_created",
        data=menu_item_data
    )

async def publish_menu_item_updated(menu_item_data: Dict[str, Any]) -> None:
    """Publish a menu item updated event."""
    await publish_event(
        topic=TOPICS["menu_events"],
        key="menu_item_updated",
        data=menu_item_data
    )

async def publish_menu_item_deleted(restaurant_id: str, menu_item_id: str) -> None:
    """Publish a menu item deleted event."""
    await publish_event(
        topic=TOPICS["menu_events"],
        key="menu_item_deleted",
        data={
            "restaurant_id": restaurant_id,
            "menu_item_id": menu_item_id
        }
    )

# Order handling events
async def publish_order_received(restaurant_id: str, order_data: Dict[str, Any]) -> None:
    """Publish an order received event."""
    await publish_event(
        topic=TOPICS["order_events"],
        key="order_received",
        data={
            "restaurant_id": restaurant_id,
            "order": order_data
        }
    )

async def publish_order_status_updated(order_id: str, restaurant_id: str, status: str) -> None:
    """Publish an order status updated event."""
    await publish_event(
        topic=TOPICS["order_events"],
        key="order_status_updated",
        data={
            "order_id": order_id,
            "restaurant_id": restaurant_id,
            "status": status
        }
    )