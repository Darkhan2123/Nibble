import os
import json
import logging
import time
from typing import Optional, Dict, Any
from faststream.kafka import KafkaBroker
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable

# Configuration
KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
logger = logging.getLogger(__name__)

# Global producer instance
producer: Optional[KafkaProducer] = None

def get_producer() -> KafkaProducer:
    """
    Get or create a Kafka producer.
    Uses lazy initialization to prevent startup failures.
    """
    global producer
    if producer is None:
        try:
            producer = KafkaProducer(
                bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                # Add more resilience with retries
                retries=5,
                retry_backoff_ms=500,
                request_timeout_ms=10000,
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Kafka producer: {e}")
            # Return a dummy producer that does nothing if Kafka is unavailable
            # This allows the service to start even if Kafka is down
            return DummyProducer()
    return producer

class DummyProducer:
    """A dummy producer that does nothing, used when Kafka is unavailable."""
    def send(self, topic, value=None, key=None, headers=None, partition=None, timestamp_ms=None):
        logger.warning(f"Kafka not available - message to topic {topic} not sent")
        return DummyFuture()

class DummyFuture:
    """A dummy future that does nothing."""
    def add_callback(self, fn, *args, **kwargs):
        pass
    
    def add_errback(self, fn, *args, **kwargs):
        pass
    
    def get(self, timeout=None):
        return None

# Initialize Kafka function
async def init_kafka():
    """Initialize Kafka setup."""
    logger.info("Initializing Kafka...")
    
    # Try to initialize Kafka with retries
    for attempt in range(3):
        try:
            # Just attempt to get the producer to test connection
            producer = get_producer()
            if not isinstance(producer, DummyProducer):
                logger.info("Kafka initialized successfully")
                return
            
            logger.warning(f"Kafka not available (attempt {attempt+1}/3), retrying in 2 seconds...")
            time.sleep(2)
        except Exception as e:
            logger.warning(f"Error initializing Kafka (attempt {attempt+1}/3): {e}")
            time.sleep(2)
    
    logger.warning("Couldn't initialize Kafka connection after 3 attempts, continuing without Kafka")

# Publish promotion events
def publish_promotion_created(promotion):
    """Publish promotion created event."""
    get_producer().send("promotions", {
        "event": "promotion_created",
        "data": promotion
    })

def publish_promotion_updated(promotion):
    """Publish promotion updated event."""
    get_producer().send("promotions", {
        "event": "promotion_updated",
        "data": promotion
    })

def publish_promotion_deleted(promotion_id):
    """Publish promotion deleted event."""
    get_producer().send("promotions", {
        "event": "promotion_deleted",
        "data": {"id": promotion_id}
    })

# Publish support ticket events
def publish_ticket_created(ticket):
    """Publish support ticket created event."""
    get_producer().send("support_tickets", {
        "event": "ticket_created",
        "data": ticket
    })

def publish_ticket_updated(ticket):
    """Publish support ticket updated event."""
    get_producer().send("support_tickets", {
        "event": "ticket_updated",
        "data": ticket
    })

def publish_ticket_resolved(ticket_id):
    """Publish support ticket resolved event."""
    get_producer().send("support_tickets", {
        "event": "ticket_resolved",
        "data": {"id": ticket_id}
    })

# Publish user events
def publish_user_banned(user_id, reason):
    """Publish user banned event."""
    get_producer().send("users", {
        "event": "user_banned",
        "data": {
            "user_id": user_id,
            "reason": reason
        }
    })

def publish_user_unbanned(user_id):
    """Publish user unbanned event."""
    get_producer().send("users", {
        "event": "user_unbanned",
        "data": {
            "user_id": user_id
        }
    })

def publish_role_assigned(user_id, role):
    """Publish role assigned event."""
    get_producer().send("users", {
        "event": "role_assigned",
        "data": {
            "user_id": user_id,
            "role": role
        }
    })

# Restaurant approval events
def publish_restaurant_approval(restaurant_id, approved):
    """Publish restaurant approval event."""
    get_producer().send("restaurant_approvals", {
        "event": "restaurant_approval",
        "data": {
            "restaurant_id": restaurant_id,
            "approved": approved
        }
    })

# Driver approval events  
def publish_driver_approval(driver_id, approved):
    """Publish driver approval event."""
    get_producer().send("driver_approvals", {
        "event": "driver_approval",
        "data": {
            "driver_id": driver_id,
            "approved": approved
        }
    })
