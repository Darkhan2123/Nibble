import logging
from typing import Dict, Any

from app.core.notification import send_user_notification

logger = logging.getLogger(__name__)

# Event handlers for direct notification events
async def handle_customer_notification(event_data: Dict[str, Any]) -> None:
    """Handle customer notification events."""
    logger.info(f"Processing customer notification: {event_data}")
    
    try:
        data = event_data.get("data", {})
        user_id = data.get("user_id")
        message = data.get("message")
        notification_type = data.get("type", "general")
        
        if not user_id or not message:
            logger.error("Missing user_id or message in customer notification event")
            return
        
        # Get reference information if available
        reference_id = data.get("reference_id")
        reference_type = data.get("reference_type")
        
        # Send notification
        await send_user_notification(
            user_id=user_id,
            title="UberEats Notification",
            message=message,
            notification_type=notification_type,
            reference_id=reference_id,
            reference_type=reference_type,
            send_push=True,
            send_email=False,
            send_sms=False
        )
        
        logger.info(f"Sent notification to customer {user_id}")
        
    except Exception as e:
        logger.error(f"Error processing customer notification: {e}")

async def handle_restaurant_notification(event_data: Dict[str, Any]) -> None:
    """Handle restaurant notification events."""
    logger.info(f"Processing restaurant notification: {event_data}")
    
    try:
        data = event_data.get("data", {})
        restaurant_id = data.get("restaurant_id")
        message = data.get("message")
        notification_type = data.get("type", "general")
        
        if not restaurant_id or not message:
            logger.error("Missing restaurant_id or message in restaurant notification event")
            return
        
        # Get reference information if available
        reference_id = data.get("reference_id")
        reference_type = data.get("reference_type")
        
        # Send notification
        await send_user_notification(
            user_id=restaurant_id,  # The user_id is the restaurant's owner user_id
            title="UberEats Restaurant Notification",
            message=message,
            notification_type=notification_type,
            reference_id=reference_id,
            reference_type=reference_type,
            send_push=True,
            send_email=False,
            send_sms=False
        )
        
        logger.info(f"Sent notification to restaurant {restaurant_id}")
        
    except Exception as e:
        logger.error(f"Error processing restaurant notification: {e}")

async def handle_driver_notification(event_data: Dict[str, Any]) -> None:
    """Handle driver notification events."""
    logger.info(f"Processing driver notification: {event_data}")
    
    try:
        data = event_data.get("data", {})
        driver_id = data.get("driver_id")
        message = data.get("message")
        notification_type = data.get("type", "general")
        
        if not driver_id or not message:
            logger.error("Missing driver_id or message in driver notification event")
            return
        
        # Get reference information if available
        reference_id = data.get("reference_id")
        reference_type = data.get("reference_type")
        
        # Send notification
        await send_user_notification(
            user_id=driver_id,  # The user_id is the driver's user_id
            title="UberEats Driver Notification",
            message=message,
            notification_type=notification_type,
            reference_id=reference_id,
            reference_type=reference_type,
            send_push=True,
            send_email=False,
            send_sms=False
        )
        
        logger.info(f"Sent notification to driver {driver_id}")
        
    except Exception as e:
        logger.error(f"Error processing driver notification: {e}")

# Event handlers for system events that generate notifications
async def handle_order_status_changed(event_data: Dict[str, Any]) -> None:
    """Handle order status changed events."""
    logger.info(f"Processing order status change: {event_data}")
    
    try:
        data = event_data.get("data", {})
        order_id = data.get("order_id")
        status = data.get("status")
        
        if not order_id or not status:
            logger.error("Missing order_id or status in order_status_changed event")
            return
        
        # This is a placeholder - in a real implementation, we would:
        # 1. Fetch the order details from the order service
        # 2. Get the customer, restaurant, and driver IDs
        # 3. Send appropriate notifications to each
        
        logger.info(f"Processed order status change for order {order_id} to {status}")
        
    except Exception as e:
        logger.error(f"Error processing order status change: {e}")

async def handle_payment_completed(event_data: Dict[str, Any]) -> None:
    """Handle payment completed events."""
    logger.info(f"Processing payment completed: {event_data}")
    
    try:
        data = event_data.get("data", {})
        order_id = data.get("order_id")
        payment_intent_id = data.get("payment_intent_id")
        
        if not order_id:
            logger.error("Missing order_id in payment_completed event")
            return
        
        # This is a placeholder - in a real implementation, we would:
        # 1. Fetch the order details from the order service
        # 2. Get the customer ID
        # 3. Send a payment confirmation notification
        
        logger.info(f"Processed payment completion for order {order_id}")
        
    except Exception as e:
        logger.error(f"Error processing payment completion: {e}")

async def handle_payment_failed(event_data: Dict[str, Any]) -> None:
    """Handle payment failed events."""
    logger.info(f"Processing payment failed: {event_data}")
    
    try:
        data = event_data.get("data", {})
        order_id = data.get("order_id")
        payment_intent_id = data.get("payment_intent_id")
        failure_reason = data.get("failure_reason", "Payment processing failed")
        
        if not order_id:
            logger.error("Missing order_id in payment_failed event")
            return
        
        # This is a placeholder - in a real implementation, we would:
        # 1. Fetch the order details from the order service
        # 2. Get the customer ID
        # 3. Send a payment failure notification
        
        logger.info(f"Processed payment failure for order {order_id}")
        
    except Exception as e:
        logger.error(f"Error processing payment failure: {e}")