import logging
import json
from datetime import datetime, timedelta
from typing import Dict, Any

from app.core.redis import (
    get_order_status, update_order_status,
    get_next_order_from_queue, remove_from_processing_queue,
    get_processing_order_data
)
from app.models.order import OrderRepository
from app.models.payment import PaymentRepository
from app.core.kafka import (
    publish_order_updated, publish_order_status_changed,
    publish_customer_notification, publish_restaurant_notification,
    publish_driver_notification, publish_analytics_event
)

logger = logging.getLogger(__name__)

order_repository = OrderRepository()
payment_repository = PaymentRepository()

# Payment event handlers
async def handle_payment_completed(event_data: Dict[str, Any]) -> None:
    """Handle payment completed event."""
    try:
        data = event_data.get("data", {})
        order_id = data.get("order_id")
        payment_intent_id = data.get("payment_intent_id")
        
        if not order_id:
            logger.error("Missing order_id in payment_completed event")
            return
        
        logger.info(f"Processing payment completed for order {order_id}")
        
        # Update order payment status
        updated_order = await order_repository.update_payment_status(
            order_id=order_id,
            payment_status="completed",
            payment_id=payment_intent_id
        )
        
        if not updated_order:
            logger.error(f"Failed to update payment status for order {order_id}")
            return
        
        # Ensure order status is updated to confirmed if it was placed
        if updated_order["status"] == "placed":
            updated_order = await order_repository.update_order_status(
                order_id=order_id,
                status="confirmed",
                updated_by="system",
                notes="Payment completed, order confirmed"
            )
            
            # Update real-time status
            await update_order_status(
                order_id=order_id,
                status="confirmed",
                data={"payment_status": "completed"}
            )
            
            # Publish events
            await publish_order_status_changed(order_id, "confirmed")
            await publish_order_updated(updated_order)
            
            # Notify customer
            await publish_customer_notification(
                user_id=updated_order["customer_id"],
                message=f"Your order #{updated_order['order_number']} has been confirmed and is being processed.",
                notification_type="order_update"
            )
            
            # Notify restaurant
            await publish_restaurant_notification(
                restaurant_id=updated_order["restaurant_id"],
                message=f"New order #{updated_order['order_number']} received.",
                notification_type="new_order"
            )
            
            # Log analytics event
            await publish_analytics_event(
                event_type="order_confirmed",
                data={
                    "order_id": order_id,
                    "order_number": updated_order["order_number"],
                    "restaurant_id": updated_order["restaurant_id"],
                    "customer_id": updated_order["customer_id"],
                    "total_amount": float(updated_order["total_amount"]),
                    "payment_method": updated_order["payment_method"]
                }
            )
            
        logger.info(f"Payment completed processing finished for order {order_id}")
        
    except Exception as e:
        logger.error(f"Error processing payment_completed event: {e}")

async def handle_payment_failed(event_data: Dict[str, Any]) -> None:
    """Handle payment failed event."""
    try:
        data = event_data.get("data", {})
        order_id = data.get("order_id")
        payment_intent_id = data.get("payment_intent_id")
        failure_reason = data.get("failure_reason", "Payment processing failed")
        
        if not order_id:
            logger.error("Missing order_id in payment_failed event")
            return
        
        logger.info(f"Processing payment failed for order {order_id}")
        
        # Update order payment status
        updated_order = await order_repository.update_payment_status(
            order_id=order_id,
            payment_status="failed",
            payment_id=payment_intent_id
        )
        
        if not updated_order:
            logger.error(f"Failed to update payment status for order {order_id}")
            return
        
        # Cancel the order due to payment failure
        updated_order = await order_repository.update_order_status(
            order_id=order_id,
            status="cancelled",
            updated_by="system",
            notes=f"Order cancelled due to payment failure: {failure_reason}"
        )
        
        # Update real-time status
        await update_order_status(
            order_id=order_id,
            status="cancelled",
            data={
                "payment_status": "failed",
                "cancellation_reason": failure_reason
            }
        )
        
        # Publish events
        await publish_order_status_changed(order_id, "cancelled")
        await publish_order_updated(updated_order)
        
        # Notify customer
        await publish_customer_notification(
            user_id=updated_order["customer_id"],
            message=f"Your order #{updated_order['order_number']} has been cancelled due to payment failure. Please try again or use a different payment method.",
            notification_type="order_update"
        )
        
        logger.info(f"Payment failed processing finished for order {order_id}")
        
    except Exception as e:
        logger.error(f"Error processing payment_failed event: {e}")

# Restaurant event handlers
async def handle_restaurant_status_changed(event_data: Dict[str, Any]) -> None:
    """Handle restaurant status changed event."""
    try:
        data = event_data.get("data", {})
        restaurant_id = data.get("restaurant_id")
        status = data.get("status")
        affected_orders = data.get("affected_orders", [])
        
        if not restaurant_id or not status:
            logger.error("Missing restaurant_id or status in restaurant_status_changed event")
            return
        
        logger.info(f"Processing restaurant status change to {status} for restaurant {restaurant_id}")
        
        # Handle restaurant closures
        if status == "closed" and affected_orders:
            for order_id in affected_orders:
                # Get the order
                order = await order_repository.get_order_by_id(order_id)
                if not order:
                    continue
                
                # Only cancel orders that are not yet preparing
                if order["status"] in ["placed", "confirmed"]:
                    # Cancel the order
                    updated_order = await order_repository.update_order_status(
                        order_id=order_id,
                        status="cancelled",
                        updated_by="system",
                        notes="Order cancelled because restaurant closed"
                    )
                    
                    # Update real-time status
                    await update_order_status(
                        order_id=order_id,
                        status="cancelled",
                        data={"cancellation_reason": "Restaurant closed"}
                    )
                    
                    # Publish events
                    await publish_order_status_changed(order_id, "cancelled")
                    await publish_order_updated(updated_order)
                    
                    # Notify customer
                    await publish_customer_notification(
                        user_id=order["customer_id"],
                        message=f"Your order #{order['order_number']} has been cancelled because the restaurant closed. We apologize for the inconvenience.",
                        notification_type="order_update"
                    )
        
        logger.info(f"Restaurant status change processing finished for restaurant {restaurant_id}")
        
    except Exception as e:
        logger.error(f"Error processing restaurant_status_changed event: {e}")

# Driver event handlers
async def handle_driver_location_updated(event_data: Dict[str, Any]) -> None:
    """Handle driver location updated event."""
    try:
        data = event_data.get("data", {})
        driver_id = data.get("driver_id")
        location = data.get("location", {})
        order_id = data.get("current_order_id")
        estimated_arrival = data.get("estimated_arrival")
        
        if not driver_id or not order_id or not estimated_arrival:
            # Not enough data to process
            return
        
        logger.info(f"Processing driver location update for order {order_id}")
        
        # Update estimated delivery time
        estimated_time = datetime.fromisoformat(estimated_arrival)
        updated_order = await order_repository.update_estimated_delivery_time(
            order_id=order_id,
            estimated_time=estimated_time
        )
        
        if not updated_order:
            logger.error(f"Failed to update estimated delivery time for order {order_id}")
            return
        
        # Update real-time status
        order_status = await get_order_status(order_id)
        if order_status and order_status["status"] == "out_for_delivery":
            await update_order_status(
                order_id=order_id,
                status="out_for_delivery",
                data={
                    "estimated_delivery_time": estimated_arrival,
                    "driver_location": location
                }
            )
            
            # Notify customer
            await publish_customer_notification(
                user_id=updated_order["customer_id"],
                message=f"Your order #{updated_order['order_number']} is on the way! Estimated delivery time: {estimated_time.strftime('%H:%M')}",
                notification_type="order_update"
            )
        
        logger.info(f"Driver location update processing finished for order {order_id}")
        
    except Exception as e:
        logger.error(f"Error processing driver_location_updated event: {e}")

async def handle_delivery_completed(event_data: Dict[str, Any]) -> None:
    """Handle delivery completed event."""
    try:
        data = event_data.get("data", {})
        order_id = data.get("order_id")
        driver_id = data.get("driver_id")
        
        if not order_id or not driver_id:
            logger.error("Missing order_id or driver_id in delivery_completed event")
            return
        
        logger.info(f"Processing delivery completed for order {order_id}")
        
        # Update order status to delivered
        updated_order = await order_repository.update_order_status(
            order_id=order_id,
            status="delivered",
            updated_by=driver_id,
            notes="Order delivered by driver"
        )
        
        if not updated_order:
            logger.error(f"Failed to update status for order {order_id}")
            return
        
        # Update real-time status
        await update_order_status(
            order_id=order_id,
            status="delivered",
            data={"actual_delivery_time": datetime.utcnow().isoformat()}
        )
        
        # Publish events
        await publish_order_status_changed(order_id, "delivered")
        await publish_order_updated(updated_order)
        
        # Notify customer
        await publish_customer_notification(
            user_id=updated_order["customer_id"],
            message=f"Your order #{updated_order['order_number']} has been delivered. Enjoy your meal!",
            notification_type="order_update"
        )
        
        # Log analytics event
        await publish_analytics_event(
            event_type="order_delivered",
            data={
                "order_id": order_id,
                "order_number": updated_order["order_number"],
                "restaurant_id": updated_order["restaurant_id"],
                "customer_id": updated_order["customer_id"],
                "driver_id": driver_id,
                "delivery_time": datetime.utcnow().isoformat()
            }
        )
        
        logger.info(f"Delivery completed processing finished for order {order_id}")
        
    except Exception as e:
        logger.error(f"Error processing delivery_completed event: {e}")

# Order processing worker
async def process_order_queue() -> None:
    """Process the order queue."""
    try:
        # Get the next order to process
        order_id = await get_next_order_from_queue()
        
        if not order_id:
            # No orders to process
            return
        
        logger.info(f"Processing order from queue: {order_id}")
        
        # Get order data
        order_data = await get_processing_order_data(order_id)
        
        if not order_data:
            # Invalid order data, remove from queue
            await remove_from_processing_queue(order_id)
            return
        
        # Process based on status
        status = order_data.get("status")
        
        if status == "payment_pending":
            # In a real system, we would wait for payment webhook/callback
            # For this mock implementation, process payment immediately
            payment_data = await payment_repository.get_payment(order_id=order_id)
            
            if payment_data:
                # Always successful for mock implementation
                await payment_repository.process_payment(
                    payment_intent_id=payment_data["payment_intent_id"],
                    success=True
                )
                
                # Payment handled by the event handler
        
        # Remove from queue after processing
        await remove_from_processing_queue(order_id)
        
        logger.info(f"Finished processing order from queue: {order_id}")
        
    except Exception as e:
        logger.error(f"Error processing order queue: {e}")

# Background worker tasks setup
async def start_background_tasks():
    """Start background tasks for order processing."""
    import asyncio
    from fastapi.concurrency import run_in_threadpool
    
    async def order_processor_task():
        """Periodic task to process the order queue."""
        while True:
            try:
                await process_order_queue()
                # Sleep for a short time before processing next order
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Error in order processor task: {e}")
                await asyncio.sleep(10)  # Sleep longer on error
    
    # Start the task
    asyncio.create_task(order_processor_task())
    logger.info("Order processor background task started")