import logging
import uuid
from typing import Dict, List, Any, Optional
from datetime import datetime
import asyncpg

from app.core.database import get_connection, transaction, fetch_one, fetch_all, execute

logger = logging.getLogger(__name__)

class PromotionRepository:
    """Repository for promotion-related database operations."""
    
    async def create_promotion(
        self,
        name: str,
        description: str,
        promo_code: str,
        discount_type: str,
        discount_value: float,
        min_order_amount: float,
        max_discount_amount: Optional[float],
        start_date: datetime,
        end_date: datetime,
        is_active: bool,
        usage_limit: Optional[int],
        applies_to: List[str],
        applies_to_ids: Optional[List[str]],
        created_by: str
    ) -> Dict[str, Any]:
        """Create a new promotion."""
        async with transaction() as tx:
            promotion_id = str(uuid.uuid4())
            
            query = """
            INSERT INTO admin_service.promotions (
                id, name, description, promo_code, discount_type, discount_value,
                min_order_amount, max_discount_amount, start_date, end_date,
                is_active, usage_limit, current_usage, applies_to, applies_to_ids,
                created_by, created_at, updated_at
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16,
                CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            RETURNING *
            """
            
            try:
                async with get_connection() as conn:
                    promotion = await conn.fetchrow(
                        query,
                        promotion_id,
                        name,
                        description,
                        promo_code,
                        discount_type,
                        discount_value,
                        min_order_amount,
                        max_discount_amount,
                        start_date,
                        end_date,
                        is_active,
                        usage_limit,
                        0,  # current_usage starts at 0
                        applies_to,
                        applies_to_ids,
                        created_by
                    )
                    
                    return dict(promotion)
                    
            except asyncpg.exceptions.UniqueViolationError:
                logger.error(f"Promo code {promo_code} already exists")
                raise ValueError(f"Promo code {promo_code} already exists")
                
            except Exception as e:
                logger.error(f"Error creating promotion: {e}")
                raise
    
    async def get_promotion_by_id(self, promotion_id: str) -> Optional[Dict[str, Any]]:
        """Get a promotion by ID."""
        query = """
        SELECT * FROM admin_service.promotions WHERE id = $1
        """
        
        return await fetch_one(query, promotion_id)
    
    async def get_promotion_by_code(self, promo_code: str) -> Optional[Dict[str, Any]]:
        """Get a promotion by promo code."""
        query = """
        SELECT * FROM admin_service.promotions WHERE promo_code = $1
        """
        
        return await fetch_one(query, promo_code)
    
    async def get_promotions(
        self,
        is_active: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get all promotions."""
        conditions = []
        params = []
        param_index = 1
        
        if is_active is not None:
            conditions.append(f"is_active = ${param_index}")
            params.append(is_active)
            param_index += 1
        
        # Build the query
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        query = f"""
        SELECT * FROM admin_service.promotions
        {where_clause}
        ORDER BY created_at DESC
        LIMIT ${param_index}
        OFFSET ${param_index + 1}
        """
        
        params.extend([limit, offset])
        
        return await fetch_all(query, *params)
    
    async def get_active_promotions(self) -> List[Dict[str, Any]]:
        """Get all active promotions."""
        now = datetime.utcnow()
        
        query = """
        SELECT * FROM admin_service.promotions
        WHERE is_active = TRUE
        AND start_date <= $1
        AND end_date >= $1
        AND (usage_limit IS NULL OR current_usage < usage_limit)
        ORDER BY created_at DESC
        """
        
        return await fetch_all(query, now)
    
    async def update_promotion(
        self,
        promotion_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        discount_type: Optional[str] = None,
        discount_value: Optional[float] = None,
        min_order_amount: Optional[float] = None,
        max_discount_amount: Optional[float] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        is_active: Optional[bool] = None,
        usage_limit: Optional[int] = None,
        applies_to: Optional[List[str]] = None,
        applies_to_ids: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """Update a promotion."""
        # Check if promotion exists
        existing_promotion = await self.get_promotion_by_id(promotion_id)
        
        if not existing_promotion:
            logger.error(f"Promotion {promotion_id} not found")
            return None
        
        # Build update query
        update_fields = []
        params = []
        param_index = 1
        
        if name is not None:
            update_fields.append(f"name = ${param_index}")
            params.append(name)
            param_index += 1
            
        if description is not None:
            update_fields.append(f"description = ${param_index}")
            params.append(description)
            param_index += 1
            
        if discount_type is not None:
            update_fields.append(f"discount_type = ${param_index}")
            params.append(discount_type)
            param_index += 1
            
        if discount_value is not None:
            update_fields.append(f"discount_value = ${param_index}")
            params.append(discount_value)
            param_index += 1
            
        if min_order_amount is not None:
            update_fields.append(f"min_order_amount = ${param_index}")
            params.append(min_order_amount)
            param_index += 1
            
        if max_discount_amount is not None:
            update_fields.append(f"max_discount_amount = ${param_index}")
            params.append(max_discount_amount)
            param_index += 1
            
        if start_date is not None:
            update_fields.append(f"start_date = ${param_index}")
            params.append(start_date)
            param_index += 1
            
        if end_date is not None:
            update_fields.append(f"end_date = ${param_index}")
            params.append(end_date)
            param_index += 1
            
        if is_active is not None:
            update_fields.append(f"is_active = ${param_index}")
            params.append(is_active)
            param_index += 1
            
        if usage_limit is not None:
            update_fields.append(f"usage_limit = ${param_index}")
            params.append(usage_limit)
            param_index += 1
            
        if applies_to is not None:
            update_fields.append(f"applies_to = ${param_index}")
            params.append(applies_to)
            param_index += 1
            
        if applies_to_ids is not None:
            update_fields.append(f"applies_to_ids = ${param_index}")
            params.append(applies_to_ids)
            param_index += 1
        
        # Add updated_at field
        update_fields.append("updated_at = CURRENT_TIMESTAMP")
        
        # If nothing to update, return the existing promotion
        if not update_fields:
            return existing_promotion
        
        # Build and execute the query
        update_clause = ", ".join(update_fields)
        params.append(promotion_id)
        
        query = f"""
        UPDATE admin_service.promotions
        SET {update_clause}
        WHERE id = ${param_index}
        RETURNING *
        """
        
        try:
            return await fetch_one(query, *params)
        except Exception as e:
            logger.error(f"Error updating promotion: {e}")
            raise
    
    async def delete_promotion(self, promotion_id: str) -> bool:
        """Delete a promotion."""
        query = """
        DELETE FROM admin_service.promotions
        WHERE id = $1
        RETURNING id
        """
        
        result = await fetch_one(query, promotion_id)
        
        return result is not None
    
    async def increment_usage(
        self,
        promotion_id: str,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Increment the usage count for a promotion."""
        # Check if promotion exists and is active
        existing_promotion = await self.get_promotion_by_id(promotion_id)
        
        if not existing_promotion:
            logger.error(f"Promotion {promotion_id} not found")
            return None
        
        # Check if promotion is active
        if not existing_promotion["is_active"]:
            logger.error(f"Promotion {promotion_id} is not active")
            return None
        
        # Check if promotion has reached usage limit
        if (existing_promotion["usage_limit"] is not None and 
            existing_promotion["current_usage"] >= existing_promotion["usage_limit"]):
            logger.error(f"Promotion {promotion_id} has reached usage limit")
            return None
        
        # Check if promotion is within valid date range
        now = datetime.utcnow()
        if (existing_promotion["start_date"] > now or 
            existing_promotion["end_date"] < now):
            logger.error(f"Promotion {promotion_id} is not valid at this time")
            return None
        
        # Check if user has already used this promotion (if it's a one-time use)
        check_query = """
        SELECT * FROM admin_service.user_promotions
        WHERE user_id = $1 AND promotion_id = $2
        """
        
        user_promo = await fetch_one(check_query, user_id, promotion_id)
        
        if user_promo:
            # Update existing user promotion record
            update_user_query = """
            UPDATE admin_service.user_promotions
            SET 
                usage_count = usage_count + 1,
                last_used_at = CURRENT_TIMESTAMP
            WHERE user_id = $1 AND promotion_id = $2
            RETURNING *
            """
            
            await fetch_one(update_user_query, user_id, promotion_id)
        else:
            # Create new user promotion record
            insert_user_query = """
            INSERT INTO admin_service.user_promotions (
                id, user_id, promotion_id, usage_count, first_used_at, last_used_at
            ) VALUES (
                $1, $2, $3, 1, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP
            )
            """
            
            await execute(insert_user_query, str(uuid.uuid4()), user_id, promotion_id)
        
        # Increment promotion usage count
        update_query = """
        UPDATE admin_service.promotions
        SET 
            current_usage = current_usage + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
        RETURNING *
        """
        
        updated_promotion = await fetch_one(update_query, promotion_id)
        
        return updated_promotion
    
    async def validate_promotion(
        self,
        promo_code: str,
        order_amount: float,
        user_id: str,
        restaurant_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Validate a promotion code.
        
        Returns the promotion if valid, None otherwise.
        """
        # Get promotion by code
        promotion = await self.get_promotion_by_code(promo_code)
        
        if not promotion:
            logger.warning(f"Promotion code {promo_code} not found")
            return None
        
        # Check if promotion is active
        if not promotion["is_active"]:
            logger.warning(f"Promotion code {promo_code} is not active")
            return None
        
        # Check if promotion is within valid date range
        now = datetime.utcnow()
        if (promotion["start_date"] > now or 
            promotion["end_date"] < now):
            logger.warning(f"Promotion code {promo_code} is not valid at this time")
            return None
        
        # Check if promotion has reached usage limit
        if (promotion["usage_limit"] is not None and 
            promotion["current_usage"] >= promotion["usage_limit"]):
            logger.warning(f"Promotion code {promo_code} has reached usage limit")
            return None
        
        # Check if order meets minimum amount
        if order_amount < promotion["min_order_amount"]:
            logger.warning(f"Order amount ${order_amount} does not meet minimum ${promotion['min_order_amount']} for promotion {promo_code}")
            return None
        
        # Check if promotion applies to this restaurant
        if (restaurant_id and "restaurant_id" in promotion["applies_to"] and 
            restaurant_id not in promotion["applies_to_ids"]):
            logger.warning(f"Promotion {promo_code} does not apply to restaurant {restaurant_id}")
            return None
        
        # All checks passed, return the promotion
        return promotion
    
    async def calculate_discount(
        self,
        promotion: Dict[str, Any],
        order_amount: float
    ) -> float:
        """
        Calculate the discount amount for a promotion.
        
        Returns the discount amount.
        """
        discount_type = promotion["discount_type"]
        discount_value = promotion["discount_value"]
        max_discount = promotion["max_discount_amount"]
        
        if discount_type == "percentage":
            # Calculate percentage discount
            discount = order_amount * (discount_value / 100)
            
            # Apply max discount if specified
            if max_discount is not None:
                discount = min(discount, max_discount)
                
        elif discount_type == "fixed_amount":
            # Fixed amount discount
            discount = discount_value
            
        elif discount_type == "free_delivery":
            # Free delivery - this would normally be handled differently
            # For now, we'll just return a fixed amount
            discount = 0  # Assume delivery fee is handled separately
            
        else:
            # Unknown discount type
            logger.error(f"Unknown discount type: {discount_type}")
            discount = 0
        
        return round(discount, 2)