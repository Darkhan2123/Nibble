import logging
from typing import Dict, List, Optional, Any
import uuid
from datetime import datetime
import json
import random

from app.core.redis import (
    create_payment_intent, update_payment_status,
    get_payment_by_intent_id, get_payment_by_order_id
)
from app.core.config import settings
from app.core.database import fetch_one, fetch_all, execute

logger = logging.getLogger(__name__)

class PaymentRepository:
    """Repository for payment-related operations."""
    
    async def create_payment(
        self,
        order_id: str,
        amount: float,
        payment_method: str,
        use_stripe: bool = False,  # Always use mock implementation
        customer_id: Optional[str] = None,
        currency: str = "usd",
        payment_method_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a payment record for an order.
        
        Uses a mock implementation for all payment processing.
        """
        try:
            # Mock implementation for development/testing
            logger.info("Using mock payment implementation")
            payment_intent_id = f"mock_{str(uuid.uuid4()).replace('-', '')}"
            client_secret = f"secret_{str(uuid.uuid4()).replace('-', '')}"
            
            # Store in database
            query = """
            INSERT INTO order_service.payments (
                payment_intent_id, order_id, amount, currency, status, 
                payment_method, client_secret, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8
            )
            RETURNING *
            """
            
            metadata = {
                "mock_payment": True,
                "customer_id": customer_id,
                "payment_method": payment_method,
                "is_test": True
            }
            
            payment_record = await fetch_one(
                query,
                payment_intent_id,
                order_id,
                amount,
                currency,
                "created",
                payment_method,
                client_secret,
                json.dumps(metadata)
            )
            
            # Also store in Redis for quick access
            await create_payment_intent(
                order_id=order_id,
                payment_intent_id=payment_intent_id,
                amount=amount
            )
            
            payment_data = dict(payment_record) if payment_record else {
                "payment_intent_id": payment_intent_id,
                "order_id": order_id,
                "amount": amount,
                "currency": currency,
                "payment_method": payment_method,
                "status": "created",
                "client_secret": client_secret,
                "created_at": datetime.utcnow().isoformat()
            }
            
            return payment_data
        except Exception as e:
            logger.error(f"Error creating payment: {str(e)}")
            raise
    
    async def process_payment(
        self,
        payment_intent_id: str,
        success: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
        use_stripe: bool = False,  # Always use mock implementation
        payment_method_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Process a payment using the mock implementation.
        
        In a real environment, this would integrate with a payment processor like Stripe.
        This implementation simulates payment processing for development and testing.
        """
        # Get payment data
        payment_data = await get_payment_by_intent_id(payment_intent_id)
        
        if not payment_data:
            # Check database too
            query = """
            SELECT * FROM order_service.payments
            WHERE payment_intent_id = $1
            """
            payment_record = await fetch_one(query, payment_intent_id)
            
            if not payment_record:
                logger.error(f"Payment intent {payment_intent_id} not found")
                return None
            
            payment_data = dict(payment_record)
        
        try:
            # Simulate payment processing
            # We'll make most payments succeed, but randomly fail about 10% of them
            # to simulate real-world payment failures
            if success and random.random() > 0.1:
                status = "completed"
                logger.info(f"MOCK PAYMENT: Successfully processed payment {payment_intent_id}")
            else:
                status = "failed"
                logger.info(f"MOCK PAYMENT: Failed to process payment {payment_intent_id}")
            
            # Add mock transaction details to metadata
            mock_metadata = {
                "transaction_id": f"mock_txn_{uuid.uuid4().hex[:8]}",
                "processor": "MockPaymentProcessor",
                "is_mock": True,
                "processed_at": datetime.utcnow().isoformat(),
                "simulation": "payment_simulation_v1"
            }
            
            # Merge with provided metadata
            if metadata:
                mock_metadata.update(metadata)
            
            # Merge with existing metadata if it exists
            existing_metadata = {}
            if payment_data.get("metadata") and isinstance(payment_data["metadata"], dict):
                existing_metadata = payment_data["metadata"]
            elif payment_data.get("metadata") and isinstance(payment_data["metadata"], str):
                try:
                    existing_metadata = json.loads(payment_data["metadata"])
                except:
                    pass
            
            mock_metadata.update(existing_metadata)
            
            # Update in Redis
            await update_payment_status(
                payment_intent_id=payment_intent_id,
                status=status,
                metadata=mock_metadata
            )
            
            # Also update in database
            query = """
            UPDATE order_service.payments
            SET status = $1, metadata = $2, updated_at = CURRENT_TIMESTAMP
            WHERE payment_intent_id = $3
            RETURNING *
            """
            
            payment_record = await fetch_one(
                query,
                status,
                json.dumps(mock_metadata),
                payment_intent_id
            )
            
            # Update order payment status
            order_id = payment_data.get("order_id")
            if order_id:
                from app.models.order import OrderRepository
                order_repo = OrderRepository()
                await order_repo.update_payment_status(
                    order_id=order_id,
                    payment_status=status,
                    payment_id=payment_intent_id
                )
            
            # Get updated payment data
            updated_payment = await get_payment_by_intent_id(payment_intent_id)
            
            return updated_payment or payment_data
                
        except Exception as e:
            logger.error(f"Error processing payment: {str(e)}")
            
            # Update payment status to error
            status = "error"
            error_metadata = {
                "error": str(e),
                "error_type": type(e).__name__,
                "processed_at": datetime.utcnow().isoformat()
            }
            
            # Merge with provided metadata
            if metadata:
                error_metadata.update(metadata)
            
            # Update in Redis
            await update_payment_status(
                payment_intent_id=payment_intent_id,
                status=status,
                metadata=error_metadata
            )
            
            # Update in database
            query = """
            UPDATE order_service.payments
            SET status = $1, metadata = $2, updated_at = CURRENT_TIMESTAMP
            WHERE payment_intent_id = $3
            RETURNING *
            """
            
            payment_record = await fetch_one(
                query,
                status,
                json.dumps(error_metadata),
                payment_intent_id
            )
            
            # Update order payment status
            order_id = payment_data.get("order_id")
            if order_id:
                from app.models.order import OrderRepository
                order_repo = OrderRepository()
                await order_repo.update_payment_status(
                    order_id=order_id,
                    payment_status="failed",
                    payment_id=payment_intent_id
                )
            
            raise ValueError(f"Payment processing error: {str(e)}")
    
    async def get_payment(
        self,
        payment_intent_id: Optional[str] = None,
        order_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Get payment data by payment intent ID or order ID."""
        # First try Redis for faster access
        if payment_intent_id:
            redis_payment = await get_payment_by_intent_id(payment_intent_id)
            if redis_payment:
                return redis_payment
            
            # If not in Redis, check database
            query = """
            SELECT * FROM order_service.payments
            WHERE payment_intent_id = $1
            """
            payment_record = await fetch_one(query, payment_intent_id)
            
            if payment_record:
                return dict(payment_record)
        
        if order_id:
            redis_payment = await get_payment_by_order_id(order_id)
            if redis_payment:
                return redis_payment
            
            # If not in Redis, check database
            query = """
            SELECT * FROM order_service.payments
            WHERE order_id = $1
            ORDER BY created_at DESC
            LIMIT 1
            """
            payment_record = await fetch_one(query, order_id)
            
            if payment_record:
                return dict(payment_record)
        
        return None
        
    async def get_payment_history(
        self,
        order_id: str
    ) -> List[Dict[str, Any]]:
        """Get payment history for an order."""
        query = """
        SELECT * FROM order_service.payments
        WHERE order_id = $1
        ORDER BY created_at DESC
        """
        
        payment_records = await fetch_all(query, order_id)
        
        return [dict(record) for record in payment_records]
        
    async def create_customer(
        self,
        user_id: str,
        email: str,
        name: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[str]:
        """
        Create a mock customer profile for a user.
        Returns a mock customer ID.
        """
        try:
            # Create a mock customer ID
            mock_customer_id = f"mock_cus_{uuid.uuid4().hex[:16]}"
            
            # Store in database
            query = """
            INSERT INTO order_service.customer_payment_profiles (
                user_id, stripe_customer_id, email, name, metadata
            ) VALUES (
                $1, $2, $3, $4, $5
            )
            ON CONFLICT (user_id) DO UPDATE SET
                stripe_customer_id = EXCLUDED.stripe_customer_id,
                email = EXCLUDED.email,
                name = EXCLUDED.name,
                metadata = EXCLUDED.metadata,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """
            
            mock_metadata = {
                "is_mock": True,
                "created_at": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            
            await fetch_one(
                query,
                user_id,
                mock_customer_id,
                email,
                name,
                json.dumps(mock_metadata)
            )
            
            logger.info(f"Created mock customer profile for user {user_id}: {mock_customer_id}")
            return mock_customer_id
            
        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            return None
            
    async def get_customer_profile(
        self,
        user_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a user's payment profile."""
        query = """
        SELECT * FROM order_service.customer_payment_profiles
        WHERE user_id = $1
        """
        
        profile = await fetch_one(query, user_id)
        
        return dict(profile) if profile else None
        
    async def add_payment_method(
        self,
        user_id: str,
        payment_method_id: str = None,
        set_as_default: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Add a mock payment method to a user's profile.
        """
        try:
            # Get customer profile
            profile = await self.get_customer_profile(user_id)
            
            if not profile or not profile.get("stripe_customer_id"):
                # Create a mock customer profile if it doesn't exist
                customer_id = await self.create_customer(
                    user_id=user_id,
                    email=f"{user_id}@example.com",
                    name=f"User {user_id}"
                )
                
                if not customer_id:
                    logger.error(f"Failed to create mock customer profile for user {user_id}")
                    return None
                
                profile = await self.get_customer_profile(user_id)
                if not profile:
                    logger.error(f"Still no customer profile found for user {user_id}")
                    return None
            
            # Generate a mock payment method ID if one wasn't provided
            if not payment_method_id:
                payment_method_id = f"mock_pm_{uuid.uuid4().hex[:16]}"
            
            # Generate mock card details
            mock_card = {
                "type": "card",
                "last4": f"{random.randint(1000, 9999)}",
                "exp_month": random.randint(1, 12),
                "exp_year": datetime.now().year + random.randint(1, 5),
                "brand": random.choice(["visa", "mastercard", "amex", "discover"])
            }
            
            # Store in database
            query = """
            INSERT INTO order_service.payment_methods (
                payment_method_id, user_id, stripe_customer_id, type, last4, 
                exp_month, exp_year, brand, is_default, metadata
            ) VALUES (
                $1, $2, $3, $4, $5, $6, $7, $8, $9, $10
            )
            ON CONFLICT (payment_method_id) DO UPDATE SET
                is_default = EXCLUDED.is_default,
                updated_at = CURRENT_TIMESTAMP
            RETURNING *
            """
            
            mock_metadata = {
                "is_mock": True,
                "created_at": datetime.utcnow().isoformat()
            }
            
            payment_method_record = await fetch_one(
                query,
                payment_method_id,
                user_id,
                profile["stripe_customer_id"],
                mock_card["type"],
                mock_card["last4"],
                mock_card["exp_month"],
                mock_card["exp_year"],
                mock_card["brand"],
                set_as_default,
                json.dumps(mock_metadata)
            )
            
            logger.info(f"Added mock payment method for user {user_id}: {payment_method_id}")
            return dict(payment_method_record) if payment_method_record else None
            
        except Exception as e:
            logger.error(f"Error adding payment method: {str(e)}")
            return None
            
    async def get_payment_methods(
        self,
        user_id: str
    ) -> List[Dict[str, Any]]:
        """Get a user's payment methods."""
        query = """
        SELECT * FROM order_service.payment_methods
        WHERE user_id = $1
        ORDER BY is_default DESC, created_at DESC
        """
        
        methods = await fetch_all(query, user_id)
        
        return [dict(method) for method in methods]