from fastapi import APIRouter, Depends, HTTPException, Path, status, Request
from typing import Dict, Any, Optional, List
import logging
import json

from app.core.auth import get_current_user, get_current_admin
from app.core.config import settings
from app.models.payment import PaymentRepository
from app.models.order import OrderRepository
from app.schemas.payment import (
    PaymentCreateRequest, PaymentProcessRequest, PaymentResponse,
    CustomerCreateRequest, PaymentMethodCreateRequest, 
    PaymentMethodResponse, CustomerProfileResponse, PaymentHistoryResponse
)
from app.core.kafka import (
    publish_payment_created, publish_payment_success, publish_payment_failed
)

logger = logging.getLogger(__name__)
router = APIRouter()
payment_repository = PaymentRepository()
order_repository = OrderRepository()

@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payment_data: PaymentCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a new payment for an order.
    
    This endpoint allows a user to create a new payment for their order. The user must be
    the customer who placed the order.
    
    If Stripe is enabled (default), this will create a Payment Intent in Stripe.
    The client then needs to confirm the payment using the client_secret.
    
    If using mock implementation (use_stripe=False), payment will be processed immediately.
    """
    # Get the order first
    order = await order_repository.get_order_by_id(payment_data.order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if the current user is the customer
    if current_user["id"] != order["customer_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only create payments for your own orders"
        )
    
    # Check if payment amount matches order total
    if abs(payment_data.amount - float(order["total_amount"])) > 0.01:  # Allow small rounding differences
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Payment amount {payment_data.amount} does not match order total {order['total_amount']}"
        )
    
    try:
        user_id = current_user["id"]
        use_stripe = payment_data.use_stripe
        
        # If using Stripe, get customer profile and payment method
        payment_method_id = payment_data.payment_method_id
        
        if use_stripe and not payment_method_id:
            # Try to get default payment method
            payment_methods = await payment_repository.get_payment_methods(user_id)
            default_methods = [m for m in payment_methods if m.get("is_default")]
            
            if default_methods:
                payment_method_id = default_methods[0]["payment_method_id"]
                logger.info(f"Using default payment method: {payment_method_id}")
        
        # Create payment
        payment = await payment_repository.create_payment(
            order_id=payment_data.order_id,
            amount=payment_data.amount,
            payment_method=payment_data.payment_method,
            use_stripe=use_stripe,
            customer_id=user_id,
            currency=payment_data.currency,
            payment_method_id=payment_method_id
        )
        
        # Publish event
        await publish_payment_created(payment)
        
        # If using Stripe, return payment intent data for client-side confirmation
        if use_stripe and "client_secret" in payment:
            logger.info(f"Created Stripe payment intent: {payment['payment_intent_id']}")
            return payment
        
        # For the mock implementation, immediately process the payment
        processed_payment = await payment_repository.process_payment(
            payment_intent_id=payment["payment_intent_id"],
            success=True,  # Always successful for mock implementation
            use_stripe=False  # Override to use mock processing
        )
        
        # Publish success event
        await publish_payment_success(processed_payment)
        
        return processed_payment
        
    except ValueError as e:
        logger.error(f"Payment validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the payment"
        )

@router.post("/process", response_model=PaymentResponse)
async def process_payment(
    payment_data: PaymentProcessRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Process a payment.
    
    With Stripe integration, this endpoint is used to complete a payment after
    client-side confirmation. For the mock implementation, this can be used to
    manually process a payment.
    """
    try:
        # Get the payment
        existing_payment = await payment_repository.get_payment(
            payment_intent_id=payment_data.payment_intent_id
        )
        
        if not existing_payment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Payment not found"
            )
        
        # Check permissions
        user_id = current_user["id"]
        user_role = current_user["role"]
        
        # Get the order
        order_id = existing_payment.get("order_id")
        order = None
        
        if order_id:
            order = await order_repository.get_order_by_id(order_id)
        
        # Only allow user who owns the order, or admin to process payment
        is_owner = order and user_id == order.get("customer_id")
        is_admin = user_role == "admin"
        
        if not (is_owner or is_admin):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to process this payment"
            )
        
        # Process the payment
        processed_payment = await payment_repository.process_payment(
            payment_intent_id=payment_data.payment_intent_id,
            success=payment_data.success,
            metadata=payment_data.metadata,
            payment_method_id=payment_data.payment_method_id
        )
        
        # Publish event
        if payment_data.success:
            await publish_payment_success(processed_payment)
        else:
            await publish_payment_failed(processed_payment)
        
        return processed_payment
        
    except ValueError as e:
        logger.error(f"Payment processing validation error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error processing payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the payment"
        )

@router.get("/{payment_intent_id}", response_model=PaymentResponse)
async def get_payment(
    payment_intent_id: str = Path(..., description="The payment intent ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a payment by its payment intent ID.
    
    This endpoint allows a user to retrieve a payment by its payment intent ID. The user
    must be the customer who placed the corresponding order, or an admin.
    """
    payment = await payment_repository.get_payment(payment_intent_id=payment_intent_id)
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found"
        )
    
    # Get the order
    order = await order_repository.get_order_by_id(payment["order_id"])
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Associated order not found"
        )
    
    # Check permissions
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    is_customer = user_id == order["customer_id"]
    is_admin = user_role == "admin"
    
    if not (is_customer or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view this payment"
        )
    
    return payment

@router.get("/order/{order_id}", response_model=PaymentResponse)
async def get_payment_by_order(
    order_id: str = Path(..., description="The order ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get a payment by its order ID.
    
    This endpoint allows a user to retrieve a payment by its order ID. The user must be
    the customer who placed the order, or an admin.
    """
    # Get the order first
    order = await order_repository.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check permissions
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    is_customer = user_id == order["customer_id"]
    is_admin = user_role == "admin"
    
    if not (is_customer or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view payments for this order"
        )
    
    # Get the payment
    payment = await payment_repository.get_payment(order_id=order_id)
    
    if not payment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payment not found for this order"
        )
    
    return payment
    
@router.post("/customer", response_model=CustomerProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_customer_profile(
    customer_data: CustomerCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Create a payment profile for a customer.
    
    This endpoint allows a user to create a payment profile in Stripe.
    This is required before adding payment methods or making payments.
    """
    try:
        user_id = current_user["id"]
        
        # Create customer in Stripe
        customer_id = await payment_repository.create_customer(
            user_id=user_id,
            email=customer_data.email,
            name=customer_data.name,
            metadata=customer_data.metadata
        )
        
        if not customer_id:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create customer profile"
            )
        
        # Get the created profile
        profile = await payment_repository.get_customer_profile(user_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve customer profile"
            )
        
        # Add empty payment methods array
        profile["payment_methods"] = []
        
        return profile
        
    except Exception as e:
        logger.error(f"Error creating customer profile: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the customer profile"
        )

@router.get("/customer/me", response_model=CustomerProfileResponse)
async def get_my_customer_profile(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the current user's payment profile.
    """
    user_id = current_user["id"]
    
    profile = await payment_repository.get_customer_profile(user_id)
    
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found"
        )
    
    # Get payment methods
    payment_methods = await payment_repository.get_payment_methods(user_id)
    
    # Add payment methods to response
    profile["payment_methods"] = payment_methods
    
    return profile

@router.post("/methods", response_model=PaymentMethodResponse, status_code=status.HTTP_201_CREATED)
async def add_payment_method(
    method_data: PaymentMethodCreateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Add a payment method to the current user's profile.
    
    This endpoint allows a user to add a payment method to their profile.
    """
    try:
        user_id = current_user["id"]
        
        # Check if customer profile exists
        profile = await payment_repository.get_customer_profile(user_id)
        
        if not profile:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer profile not found. Create a profile first."
            )
        
        # Add payment method
        payment_method = await payment_repository.add_payment_method(
            user_id=user_id,
            payment_method_id=method_data.payment_method_id,
            set_as_default=method_data.set_as_default
        )
        
        if not payment_method:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to add payment method"
            )
        
        return payment_method
        
    except Exception as e:
        logger.error(f"Error adding payment method: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while adding the payment method"
        )

@router.get("/methods", response_model=List[PaymentMethodResponse])
async def get_payment_methods(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the current user's payment methods.
    """
    user_id = current_user["id"]
    
    payment_methods = await payment_repository.get_payment_methods(user_id)
    
    return payment_methods

@router.get("/history/{order_id}", response_model=PaymentHistoryResponse)
async def get_payment_history(
    order_id: str = Path(..., description="The order ID"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get payment history for an order.
    
    This endpoint allows a user to retrieve the payment history for an order.
    The user must be the customer who placed the order, or an admin.
    """
    # Get the order first
    order = await order_repository.get_order_by_id(order_id)
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check permissions
    user_id = current_user["id"]
    user_role = current_user["role"]
    
    is_customer = user_id == order["customer_id"]
    is_admin = user_role == "admin"
    
    if not (is_customer or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to view payment history for this order"
        )
    
    # Get payment history
    payments = await payment_repository.get_payment_history(order_id)
    
    return {
        "payments": payments,
        "total_count": len(payments)
    }
    
@router.post("/webhook", status_code=status.HTTP_200_OK)
async def payment_webhook(
    request: Request
):
    """
    Mock webhook for receiving payment events.
    
    This endpoint simulates receiving webhooks from a payment processor.
    In production, this would be called by services like Stripe when
    payment events occur.
    """
    try:
        # Read the request body
        payload = await request.body()
        
        try:
            # Assume JSON payload
            event_data = json.loads(payload.decode("utf-8"))
        except json.JSONDecodeError:
            # If not valid JSON, create a simple mock event
            event_data = {
                "type": "mock.payment_event",
                "data": {
                    "object": {
                        "id": "mock_event_" + str(hash(payload))[:8],
                    }
                }
            }
        
        # Get the event type
        event_type = event_data.get("type", "mock.payment_event")
        logger.info(f"Received mock payment event: {event_type}")
        
        # Process any payments that might be associated with this webhook
        # Just log the event, but don't actually do anything with it
        # In a real implementation, we'd use the webhook to update payment statuses
        
        return {
            "status": "success", 
            "message": f"Processed mock webhook event: {event_type}"
        }
        
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while processing the webhook"
        )