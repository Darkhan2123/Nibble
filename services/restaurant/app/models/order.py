import logging
from typing import Dict, List, Optional, Any
import json

from app.core.database import fetch_one, fetch_all, execute
from app.core.kafka import publish_order_status_updated

logger = logging.getLogger(__name__)

class RestaurantOrderRepository:
    """Repository for restaurant order operations."""
    
    async def get_restaurant_orders(
        self,
        restaurant_id: str,
        status: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get orders for a restaurant."""
        # Note: In a real world scenario, this would likely be in the order service
        # For this demo, we'll implement a simplified version
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
    
    async def get_active_orders(
        self,
        restaurant_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get active orders for a restaurant."""
        # Active orders are those that are in the processing stage
        active_statuses = ["placed", "confirmed", "preparing", "ready_for_pickup"]
        
        placeholders = []
        params = [restaurant_id]
        param_index = 2
        
        for _ in active_statuses:
            placeholders.append(f"${param_index}")
            params.append(_)
            param_index += 1
        
        query = f"""
        SELECT o.*, 
               (SELECT json_agg(oi.*) FROM order_service.order_items oi 
                WHERE oi.order_id = o.id) AS items
        FROM order_service.orders o
        WHERE restaurant_id = $1
          AND status IN ({", ".join(placeholders)})
        ORDER BY o.created_at DESC
        LIMIT ${param_index}
        OFFSET ${param_index + 1}
        """
        
        params.extend([limit, offset])
        
        return await fetch_all(query, *params)
    
    async def get_order_by_id(
        self,
        order_id: str,
        restaurant_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get an order by ID for a specific restaurant."""
        query = """
        SELECT o.*, 
               (SELECT json_agg(oi.*) FROM order_service.order_items oi 
                WHERE oi.order_id = o.id) AS items
        FROM order_service.orders o
        WHERE o.id = $1 AND o.restaurant_id = $2
        """
        
        return await fetch_one(query, order_id, restaurant_id)
    
    async def update_order_status(
        self,
        order_id: str,
        restaurant_id: str,
        status: str,
        notes: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Update an order's status."""
        # Valid status transitions for a restaurant
        valid_status_transitions = {
            "placed": ["confirmed", "cancelled"],
            "confirmed": ["preparing", "cancelled"],
            "preparing": ["ready_for_pickup", "cancelled"],
            "ready_for_pickup": ["out_for_delivery", "picked_up"],
            # No further transitions after out_for_delivery or picked_up
        }
        
        # Get the current order
        current_order = await self.get_order_by_id(order_id, restaurant_id)
        
        if not current_order:
            logger.error(f"Order {order_id} not found for restaurant {restaurant_id}")
            return None
        
        current_status = current_order["status"]
        
        # Check if the transition is valid
        if current_status not in valid_status_transitions or status not in valid_status_transitions.get(current_status, []):
            logger.error(f"Invalid status transition from {current_status} to {status}")
            raise ValueError(f"Invalid status transition from {current_status} to {status}")
        
        # Update the order status
        query = """
        UPDATE order_service.orders
        SET status = $1, updated_at = CURRENT_TIMESTAMP
        WHERE id = $2 AND restaurant_id = $3
        RETURNING *
        """
        
        updated_order = await fetch_one(query, status, order_id, restaurant_id)
        
        if updated_order:
            # Record the status change in history
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
                restaurant_id,  # Using restaurant_id as a proxy for the user who updated it
                notes
            )
            
            # Publish the status change event
            await publish_order_status_updated(
                order_id=order_id,
                restaurant_id=restaurant_id,
                status=status
            )
        
        return updated_order
    
    async def get_order_history(
        self,
        restaurant_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> Dict[str, Any]:
        """Get order history for a restaurant."""
        conditions = ["restaurant_id = $1"]
        params = [restaurant_id]
        param_index = 2
        
        if start_date:
            conditions.append(f"created_at >= ${param_index}")
            params.append(start_date)
            param_index += 1
            
        if end_date:
            conditions.append(f"created_at <= ${param_index}")
            params.append(end_date)
            param_index += 1
            
        where_clause = " AND ".join(conditions)
        
        # Get total count
        count_query = f"""
        SELECT COUNT(*) FROM order_service.orders
        WHERE {where_clause}
        """
        
        total_count = await fetch_one(count_query, *params)
        
        # Get orders
        query = f"""
        SELECT * FROM order_service.orders
        WHERE {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_index}
        OFFSET ${param_index + 1}
        """
        
        params.extend([limit, offset])
        
        orders = await fetch_all(query, *params)
        
        return {
            "total": total_count["count"],
            "limit": limit,
            "offset": offset,
            "orders": orders
        }
    
    async def get_order_statistics(
        self,
        restaurant_id: str,
        period: str = "day"  # 'day', 'week', 'month', 'year'
    ) -> Dict[str, Any]:
        """Get order statistics for a restaurant."""
        # This would typically query the analytics service
        # For now, we'll return placeholder data
        return {
            "total_orders": 0,
            "completed_orders": 0,
            "cancelled_orders": 0,
            "average_preparation_time": 0,
            "average_order_value": 0,
            "total_revenue": 0,
            "period": period
        }