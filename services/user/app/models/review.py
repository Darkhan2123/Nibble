import logging
import uuid
from typing import Dict, List, Optional, Any
import asyncpg
from datetime import datetime

from app.core.database import get_connection, transaction, fetch_one, fetch_all, execute

logger = logging.getLogger(__name__)

class ReviewRepository:
    """Repository for review-related database operations."""
    
    async def create_review(
        self,
        customer_id: str,
        order_id: str,
        restaurant_id: str,
        driver_id: Optional[str] = None,
        food_rating: Optional[int] = None,
        delivery_rating: Optional[int] = None,
        review_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a new review for an order."""
        query = """
        INSERT INTO order_service.ratings (
            customer_id, order_id, restaurant_id, driver_id,
            food_rating, delivery_rating, review_text, reviewed_at
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, CURRENT_TIMESTAMP
        )
        RETURNING *
        """
        
        try:
            review = await fetch_one(
                query,
                customer_id,
                order_id,
                restaurant_id,
                driver_id,
                food_rating,
                delivery_rating,
                review_text
            )
            
            # Update restaurant average rating if food rating is provided
            if food_rating is not None:
                await self._update_restaurant_rating(restaurant_id, food_rating)
            
            # Update driver average rating if delivery rating is provided
            if delivery_rating is not None and driver_id is not None:
                await self._update_driver_rating(driver_id, delivery_rating)
            
            return review
        except asyncpg.UniqueViolationError:
            logger.error(f"Review already exists for order {order_id}")
            raise ValueError(f"Review already exists for this order")
        except Exception as e:
            logger.error(f"Error creating review: {e}")
            raise
    
    async def _update_restaurant_rating(self, restaurant_id: str, new_rating: int) -> None:
        """Update a restaurant's average rating."""
        query = """
        UPDATE restaurant_service.restaurant_profiles
        SET 
            average_rating = (average_rating * total_ratings + $1) / (total_ratings + 1),
            total_ratings = total_ratings + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = $2
        """
        
        try:
            await execute(query, new_rating, restaurant_id)
        except Exception as e:
            logger.error(f"Error updating restaurant rating: {e}")
            # We don't want to fail the review creation if rating update fails
            pass
    
    async def _update_driver_rating(self, driver_id: str, new_rating: int) -> None:
        """Update a driver's average rating."""
        query = """
        UPDATE driver_service.driver_profiles
        SET 
            average_rating = (average_rating * total_deliveries + $1) / (total_deliveries + 1),
            total_deliveries = total_deliveries + 1,
            updated_at = CURRENT_TIMESTAMP
        WHERE user_id = $2
        """
        
        try:
            await execute(query, new_rating, driver_id)
        except Exception as e:
            logger.error(f"Error updating driver rating: {e}")
            # We don't want to fail the review creation if rating update fails
            pass
    
    async def get_review_by_order_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        """Get a review by order ID."""
        query = """
        SELECT * FROM order_service.ratings
        WHERE order_id = $1
        """
        
        return await fetch_one(query, order_id)
    
    async def get_restaurant_reviews(
        self,
        restaurant_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get reviews for a restaurant."""
        query = """
        SELECT
            r.*,
            u.first_name,
            u.last_name,
            u.profile_picture_url
        FROM order_service.ratings r
        JOIN user_service.users u ON r.customer_id = u.id
        WHERE r.restaurant_id = $1
        ORDER BY r.reviewed_at DESC
        LIMIT $2 OFFSET $3
        """
        
        return await fetch_all(query, restaurant_id, limit, offset)
    
    async def get_driver_reviews(
        self,
        driver_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get reviews for a driver."""
        query = """
        SELECT
            r.*,
            u.first_name,
            u.last_name,
            u.profile_picture_url
        FROM order_service.ratings r
        JOIN user_service.users u ON r.customer_id = u.id
        WHERE r.driver_id = $1
        ORDER BY r.reviewed_at DESC
        LIMIT $2 OFFSET $3
        """
        
        return await fetch_all(query, driver_id, limit, offset)
    
    async def get_user_reviews(
        self,
        user_id: str,
        limit: int = 20,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get reviews written by a user."""
        query = """
        SELECT
            r.*,
            res.name as restaurant_name,
            res.logo_url as restaurant_logo
        FROM order_service.ratings r
        JOIN restaurant_service.restaurant_profiles res ON r.restaurant_id = res.id
        WHERE r.customer_id = $1
        ORDER BY r.reviewed_at DESC
        LIMIT $2 OFFSET $3
        """
        
        return await fetch_all(query, user_id, limit, offset)
    
    async def update_review_response(
        self,
        review_id: str,
        response_text: str
    ) -> Optional[Dict[str, Any]]:
        """
        Update the response to a review.
        This is used by restaurant owners to respond to customer reviews.
        """
        query = """
        UPDATE order_service.ratings
        SET 
            review_response = $1,
            response_at = CURRENT_TIMESTAMP
        WHERE id = $2
        RETURNING *
        """
        
        return await fetch_one(query, response_text, review_id)