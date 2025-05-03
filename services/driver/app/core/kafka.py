import logging
import json
import uuid
from datetime import datetime
from typing import Any, Dict, List, Callable, Awaitable
from faststream.kafka import KafkaBroker
# Using KafkaBroker only as KafkaProducer may not be available in current version

from app.core.config import settings

logger = logging.getLogger(__name__)

# Define Kafka topics
TOPICS = {
    "driver_events": "driver-events",
    "delivery_events": "delivery-events",
    "order_events": "order-events",
    "location_events": "location-events",
}

# Global Kafka broker
kafka_broker: KafkaBroker = None

async def init_kafka() -> None:
    """Initialize the Kafka broker."""
    global kafka_broker
    try:
        logger.info("Creating Kafka broker")
        # Add kafka-python package to ensure compatibility
        try:
            import kafka
            logger.info(f"Using kafka-python version: {kafka.__version__}")
        except ImportError:
            logger.warning("kafka-python package is not installed - will proceed with limited functionality")
            
        kafka_broker = KafkaBroker(settings.KAFKA_BOOTSTRAP_SERVERS)
        logger.info("Kafka broker created successfully")
    except Exception as e:
        logger.error(f"Failed to create Kafka broker: {e}")
        logger.warning("Continuing without Kafka for initial testing")
        return None

async def get_kafka_producer():
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
            "service": "driver-service",
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

# Driver-specific events
async def publish_driver_registered(driver_data: Dict[str, Any]) -> None:
    """Publish a driver registered event."""
    await publish_event(
        topic=TOPICS["driver_events"],
        key="driver_registered",
        data=driver_data
    )

async def publish_driver_updated(driver_data: Dict[str, Any]) -> None:
    """Publish a driver updated event."""
    await publish_event(
        topic=TOPICS["driver_events"],
        key="driver_updated",
        data=driver_data
    )

async def publish_driver_location_updated(driver_id: str, latitude: float, longitude: float, is_available: bool) -> None:
    """Publish a driver location updated event."""
    await publish_event(
        topic=TOPICS["location_events"],
        key="driver_location_updated",
        data={
            "driver_id": driver_id,
            "latitude": latitude,
            "longitude": longitude,
            "is_available": is_available,
            "timestamp": datetime.utcnow().isoformat()
        }
    )

async def publish_driver_availability_changed(driver_id: str, is_available: bool) -> None:
    """Publish a driver availability changed event."""
    await publish_event(
        topic=TOPICS["driver_events"],
        key="driver_availability_changed",
        data={
            "driver_id": driver_id,
            "is_available": is_available
        }
    )

# Delivery-specific events
async def publish_delivery_assigned(delivery_data: Dict[str, Any]) -> None:
    """Publish a delivery assigned event."""
    await publish_event(
        topic=TOPICS["delivery_events"],
        key="delivery_assigned",
        data=delivery_data
    )

async def publish_delivery_started(delivery_data: Dict[str, Any]) -> None:
    """Publish a delivery started event."""
    await publish_event(
        topic=TOPICS["delivery_events"],
        key="delivery_started",
        data=delivery_data
    )

async def publish_delivery_completed(delivery_data: Dict[str, Any]) -> None:
    """Publish a delivery completed event."""
    await publish_event(
        topic=TOPICS["delivery_events"],
        key="delivery_completed",
        data=delivery_data
    )

async def publish_delivery_failed(delivery_data: Dict[str, Any]) -> None:
    """Publish a delivery failed event."""
    await publish_event(
        topic=TOPICS["delivery_events"],
        key="delivery_failed",
        data=delivery_data
    )

# Order-specific events
async def publish_order_status_updated(order_id: str, driver_id: str, status: str) -> None:
    """Publish an order status updated event."""
    await publish_event(
        topic=TOPICS["order_events"],
        key="order_status_updated",
        data={
            "order_id": order_id,
            "driver_id": driver_id,
            "status": status
        }
    )
    
async def publish_delivery_location_updated(order_id: str, driver_id: str, latitude: float, 
                                         longitude: float, status: str) -> None:
    """Publish a delivery location updated event."""
    await publish_event(
        topic=TOPICS["location_events"],
        key="delivery_location_updated",
        data={
            "order_id": order_id,
            "driver_id": driver_id,
            "latitude": latitude,
            "longitude": longitude,
            "status": status,
            "timestamp": datetime.utcnow().isoformat()
        }
    )