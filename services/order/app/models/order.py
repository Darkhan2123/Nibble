import logging
import uuid
from typing import Dict, List, Optional, Any
import asyncpg
from datetime import datetime
import random
import string

from app.core.database import get_connection, transaction, fetch_one, fetch_all, execute
from app.core.config import settings

logger = logging.getLogger(__name__)

class OrderRepository:
    """Repository for order-related database operations."""
    
    async def create_order(
        self,
        customer_id: str,
        restaurant_id: str,
        address_id: str,
        items: List[Dict[str, Any]],
        subtotal: float,
        delivery_fee: float,
        payment_method: str,
        special_instructions: Optional[str] = None,
        promo_discount: float = 0,
    ) -> Dict[str, Any]:
        """Create a new order."""
        async with transaction() as tx:
            order_id = str(uuid.uuid4())
            
            # Generate order number
            order_number = self._generate_order_number()
            
            # Calculate tax
            tax = round(subtotal * settings.DEFAULT_TAX_RATE, 2)
            
            # Calculate total
            total_amount = round(subtotal + tax + delivery_fee - promo_discount, 2)
            
            query = """
            INSERT INTO order_service.orders (
                id, order_number, customer_id, restaurant_id, status,
                subtotal, tax, delivery_fee, promo_discount, total_amount,
                payment_method, payment_status, delivery_address_id, special_instructions
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14
            )
            RETURNING *
            """
            
            try:
                async with get_connection() as conn:
                    order = await conn.fetchrow(
                        query,
                        order_id,
                        order_number,
                        customer_id,
                        restaurant_id,
                        "placed",  # Initial status
                        subtotal,
                        tax,
                        delivery_fee,
                        promo_discount,
                        total_amount,
                        payment_method,
                        "pending",  # Initial payment status
                        address_id,
                        special_instructions
                    )
                    
                    # Create order items
                    for item in items:
                        item_query = """
                        INSERT INTO order_service.order_items (
                            id, order_id, menu_item_id, menu_item_name, quantity,
                            unit_price, subtotal, special_instructions, customizations
                        ) VALUES (
                            $1, $2, $3, $4, $5, $6, $7, $8, $9
                        )
                        """
                        
                        item_id = str(uuid.uuid4())
                        item_subtotal = round(item["unit_price"] * item["quantity"], 2)
                        
                        await conn.execute(
                            item_query,
                            item_id,
                            order_id,
                            item["menu_item_id"],
                            item["menu_item_name"],
                            item["quantity"],
                            item["unit_price"],
                            item_subtotal,
                            item.get("special_instructions"),
                            item.get("customizations")
                        )
                    
                    # Record initial status in history
                    history_query = """
                    INSERT INTO order_service.order_status_history (
                        order_id, status, updated_by_user_id, notes
                    ) VALUES (
                        $1, $2, $3, $4
                    )
                    """
                    
                    await conn.execute(
                        history_query,
                        order_id,
                        "placed",
                        customer_id,
                        "Order placed"
                    )
                    
                    order_dict = dict(order)
                    
                    # Fetch order items
                    items_query = """
                    SELECT * FROM order_service.order_items
                    WHERE order_id = $1
                    """
                    
                    order_items = await conn.fetch(items_query, order_id)
                    order_dict["items"] = [dict(item) for item in order_items]
                    
                    return order_dict
                    
            except Exception as e:
                logger.error(f"Error creating order: {e}")
                raise
    
    def _generate_order_number(self) -> str:
        """Generate a unique order number."""
        prefix = settings.ORDER_NUMBER_PREFIX
        timestamp = int(datetime.utcnow().timestamp())
        random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"{prefix}{timestamp}{random_chars}"
    
    async def get_order_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get an order by ID."""
        query = """
        SELECT o.*, 
               (SELECT json_agg(oi.*) FROM order_service.order_items oi 
                WHERE oi.order_id = o.id) AS items
        FROM order_service.orders o
        WHERE o.id = $1
        """
        
        return await fetch_one(query, order_id)
    
    async def get_order_by_number(self, order_number: str) -> Optional[Dict[str, Any]]:
        """Get an order by its order number."""
        query = """
        SELECT o.*, 
               (SELECT json_agg(oi.*) FROM order_service.order_items oi 
                WHERE oi.order_id = o.id) AS items
        FROM order_service.orders o
        WHERE o.order_number = $1
        """
        
        return await fetch_one(query, order_number)
    
    async def get_orders_by_customer(
        self,
        customer_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get orders for a customer."""
        conditions = ["customer_id = $1"]
        params = [customer_id]
        param_index = 2
        
        if status:
            conditions.append(f"status = ${param_index}")
            params.append(status)
            param_index += 1
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        SELECT o.*, 
               (SELECT json_agg(oi.*) FROM order_service.order_items oi 
                WHERE oi.order_id = o.id) AS items
        FROM order_service.orders o
        WHERE {where_clause}
        ORDER BY o.created_at DESC
        LIMIT ${param_index}
        OFFSET ${param_index + 1}
        """
        
        params.extend([limit, offset])
        
        return await fetch_all(query, *params)
    
    async def get_orders_by_restaurant(
        self,
        restaurant_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get orders for a restaurant."""
        conditions = ["restaurant_id = $1"]
        params = [restaurant_id]
        param_index = 2
        
        if status:
            conditions.append(f"status = ${param_index}")
            params.append(status)
            param_index += 1
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        SELECT o.*, 
               (SELECT json_agg(oi.*) FROM order_service.order_items oi 
                WHERE oi.order_id = o.id) AS items
        FROM order_service.orders o
        WHERE {where_clause}
        ORDER BY o.created_at DESC
        LIMIT ${param_index}
        OFFSET ${param_index + 1}
        """
        
        params.extend([limit, offset])
        
        return await fetch_all(query, *params)
    
    async def update_order_status(
        self,
        order_id: str,
        status: str,
        updated_by: str,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update an order's status."""
        # Check if order exists
        existing_order = await self.get_order_by_id(order_id)
        
        if not existing_order:
            logger.error(f"Order {order_id} not found")
            return None
        
        # Valid status transitions
        valid_status_map = {
            "placed": ["confirmed", "cancelled"],
            "confirmed": ["preparing", "cancelled"],
            "preparing": ["ready_for_pickup", "cancelled"],
            "ready_for_pickup": ["out_for_delivery", "cancelled"],
            "out_for_delivery": ["delivered", "cancelled"],
            "delivered": [],  # Terminal state
            "cancelled": []   # Terminal state
        }
        
        current_status = existing_order["status"]
        
        # Check if transition is valid
        if status not in valid_status_map.get(current_status, []):
            logger.error(f"Invalid status transition from {current_status} to {status}")
            raise ValueError(f"Invalid status transition from {current_status} to {status}")
        
        # Update order status
        query = """
        UPDATE order_service.orders
        SET status = $1, updated_at = CURRENT_TIMESTAMP
        WHERE id = $2
        RETURNING *
        """
        
        updated_order = await fetch_one(query, status, order_id)
        
        if updated_order:
            # Record status change in history
            history_query = """
            INSERT INTO order_service.order_status_history (
                order_id, status, updated_by_user_id, notes
            ) VALUES (
                $1, $2, $3, $4
            )
            """
            
            await execute(
                history_query,
                order_id,
                status,
                updated_by,
                notes or f"Status changed to {status}"
            )
            
            # If status is delivered, update actual delivery time
            if status == "delivered":
                await execute(
                    """
                    UPDATE order_service.orders
                    SET actual_delivery_time = CURRENT_TIMESTAMP
                    WHERE id = $1
                    """,
                    order_id
                )
            
            # If status is cancelled, update cancellation info
            if status == "cancelled":
                await execute(
                    """
                    UPDATE order_service.orders
                    SET 
                        cancellation_time = CURRENT_TIMESTAMP,
                        cancellation_reason = $1,
                        cancelled_by = $2
                    WHERE id = $3
                    """,
                    notes or "Order cancelled",
                    updated_by,
                    order_id
                )
        
        # Get the updated order with items
        return await self.get_order_by_id(order_id)
    
    async def update_payment_status(
        self,
        order_id: str,
        payment_status: str,
        payment_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update an order's payment status."""
        # Check if order exists
        existing_order = await self.get_order_by_id(order_id)
        
        if not existing_order:
            logger.error(f"Order {order_id} not found")
            return None
        
        # Valid payment status transitions
        valid_status = ["pending", "completed", "failed", "refunded"]
        
        if payment_status not in valid_status:
            logger.error(f"Invalid payment status: {payment_status}")
            raise ValueError(f"Invalid payment status: {payment_status}")
        
        # Update payment status
        query = """
        UPDATE order_service.orders
        SET 
            payment_status = $1,
            stripe_payment_id = COALESCE($2, stripe_payment_id),
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $3
        RETURNING *
        """
        
        updated_order = await fetch_one(query, payment_status, payment_id, order_id)
        
        # Get the updated order with items
        return await self.get_order_by_id(order_id)
    
    async def update_driver_assignment(
        self,
        order_id: str,
        driver_id: str
    ) -> Optional[Dict[str, Any]]:
        """Assign a driver to an order."""
        # Check if order exists and is in a valid state for driver assignment
        query_order = """
        SELECT * FROM order_service.orders
        WHERE id = $1 AND status = 'ready_for_pickup'
        """
        
        existing_order = await fetch_one(query_order, order_id)
        
        if not existing_order:
            logger.error(f"Order {order_id} not found or not ready for pickup")
            return None
        
        # Assign driver
        update_query = """
        UPDATE order_service.orders
        SET driver_id = $1, updated_at = CURRENT_TIMESTAMP
        WHERE id = $2
        RETURNING *
        """
        
        updated_order = await fetch_one(update_query, driver_id, order_id)
        
        # Record assignment in history
        if updated_order:
            history_query = """
            INSERT INTO order_service.order_status_history (
                order_id, status, updated_by_user_id, notes
            ) VALUES (
                $1, $2, $3, $4
            )
            """
            
            await execute(
                history_query,
                order_id,
                existing_order["status"],
                driver_id,
                "Driver assigned"
            )
        
        # Get the updated order with items
        return await self.get_order_by_id(order_id)
    
    async def update_estimated_delivery_time(
        self,
        order_id: str,
        estimated_time: datetime
    ) -> Optional[Dict[str, Any]]:
        """Update the estimated delivery time for an order."""
        query = """
        UPDATE order_service.orders
        SET estimated_delivery_time = $1, updated_at = CURRENT_TIMESTAMP
        WHERE id = $2
        RETURNING *
        """
        
        await fetch_one(query, estimated_time, order_id)
        
        # Get the updated order with items
        return await self.get_order_by_id(order_id)
    
    async def add_tip(
        self,
        order_id: str,
        tip_amount: float
    ) -> Optional[Dict[str, Any]]:
        """Add or update tip for an order."""
        # Check if order exists
        existing_order = await self.get_order_by_id(order_id)
        
        if not existing_order:
            logger.error(f"Order {order_id} not found")
            return None
        
        # Validate tip amount
        if tip_amount < 0:
            raise ValueError("Tip amount cannot be negative")
        
        # Update tip and total amount
        query = """
        UPDATE order_service.orders
        SET 
            tip = $1,
            total_amount = total_amount - COALESCE(tip, 0) + $1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $2
        RETURNING *
        """
        
        await fetch_one(query, tip_amount, order_id)
        
        # Get the updated order with items
        return await self.get_order_by_id(order_id)
    
    async def add_rating(
        self,
        order_id: str,
        customer_id: str,
        food_rating: Optional[int] = None,
        delivery_rating: Optional[int] = None,
        review_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Add a rating for an order."""
        # Check if order exists and belongs to customer
        query_order = """
        SELECT * FROM order_service.orders
        WHERE id = $1 AND customer_id = $2 AND status = 'delivered'
        """
        
        existing_order = await fetch_one(query_order, order_id, customer_id)
        
        if not existing_order:
            logger.error(f"Order {order_id} not found, not delivered, or not owned by customer {customer_id}")
            raise ValueError("Cannot rate this order")
        
        # Check if rating already exists
        query_rating = """
        SELECT * FROM order_service.ratings
        WHERE order_id = $1
        """
        
        existing_rating = await fetch_one(query_rating, order_id)
        
        if existing_rating:
            logger.error(f"Rating already exists for order {order_id}")
            raise ValueError("Order already has a rating")
        
        # Validate ratings
        if food_rating is not None and (food_rating < 1 or food_rating > 5):
            raise ValueError("Food rating must be between 1 and 5")
        
        if delivery_rating is not None and (delivery_rating < 1 or delivery_rating > 5):
            raise ValueError("Delivery rating must be between 1 and 5")
        
        # Create rating
        query = """
        INSERT INTO order_service.ratings (
            id, order_id, customer_id, restaurant_id, driver_id,
            food_rating, delivery_rating, review_text
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8
        )
        RETURNING *
        """
        
        rating_id = str(uuid.uuid4())
        rating = await fetch_one(
            query,
            rating_id,
            order_id,
            customer_id,
            existing_order["restaurant_id"],
            existing_order["driver_id"],
            food_rating,
            delivery_rating,
            review_text
        )
        
        # Update restaurant rating if food rating provided
        if food_rating is not None:
            # This would typically be handled by a trigger or a separate service
            # For simplicity, we'll update it directly here
            await execute(
                """
                UPDATE restaurant_service.restaurant_profiles
                SET 
                    average_rating = (average_rating * total_ratings + $1) / (total_ratings + 1),
                    total_ratings = total_ratings + 1
                WHERE id = $2
                """,
                food_rating,
                existing_order["restaurant_id"]
            )
        
        # Update driver rating if delivery rating provided
        if delivery_rating is not None and existing_order["driver_id"]:
            # This would typically be handled by a trigger or a separate service
            # For simplicity, we'll update it directly here
            await execute(
                """
                UPDATE driver_service.driver_profiles
                SET 
                    average_rating = (average_rating * total_deliveries + $1) / (total_deliveries + 1)
                WHERE user_id = $2
                """,
                delivery_rating,
                existing_order["driver_id"]
            )
        
        return dict(rating)
    
    async def get_order_status_history(
        self,
        order_id: str
    ) -> List[Dict[str, Any]]:
        """Get the status history for an order."""
        query = """
        SELECT * FROM order_service.order_status_history
        WHERE order_id = $1
        ORDER BY created_at
        """
        
        return await fetch_all(query, order_id)
        
    async def get_active_orders_by_driver(self, driver_id: str) -> List[Dict[str, Any]]:
        """
        Get all active orders assigned to a driver.
        Active orders are those with status 'ready_for_pickup' or 'out_for_delivery'.
        """
        query = """
        SELECT o.*, 
               (SELECT json_agg(oi.*) FROM order_service.order_items oi WHERE oi.order_id = o.id) AS items
        FROM order_service.orders o
        WHERE o.driver_id = $1
        AND o.status IN ('ready_for_pickup', 'out_for_delivery')
        ORDER BY o.created_at DESC
        """
        
        try:
            orders = await fetch_all(query, driver_id)
            return orders
        except Exception as e:
            logger.error(f"Error fetching active orders for driver {driver_id}: {e}")
            return []