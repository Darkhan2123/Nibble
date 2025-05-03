from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Dict, Any, List, Optional
import logging
import aiohttp
from app.core.auth import validate_token
from app.models.address import AddressRepository
from app.core.config import get_settings
from pydantic import BaseModel

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()

class OrderItem(BaseModel):
    menu_item_id: str
    quantity: int
    special_instructions: Optional[str] = None
    customizations: Optional[Dict[str, List[str]]] = None

class OrderCreate(BaseModel):
    restaurant_id: str
    address_id: str
    items: List[OrderItem]
    special_instructions: Optional[str] = None
    payment_method: str = "stripe"  # In a real system, you'd have multiple options

class OrderResponse(BaseModel):
    id: str
    status: str
    total_amount: float
    estimated_delivery_time: Optional[int] = None  # in minutes

class PaymentResponse(BaseModel):
    success: bool
    message: str
    order_id: Optional[str] = None

@router.post("/", response_model=OrderResponse, summary="Create a new order")
async def create_order(
    order: OrderCreate,
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Create a new order from the current user.
    """
    address_repo = AddressRepository()
    
    # Validate the address belongs to the user
    address = await address_repo.get_address_by_id(order.address_id, token["user_id"])
    
    if not address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found or doesn't belong to you"
        )
    
    # Forward the order to the order service
    try:
        order_service_url = "http://order:8003/api/v1/orders"
        
        # Prepare the order data
        order_data = {
            "customer_id": token["user_id"],
            "restaurant_id": order.restaurant_id,
            "address_id": order.address_id,
            "items": [item.dict() for item in order.items],
            "special_instructions": order.special_instructions,
            "payment_method": order.payment_method
        }
        
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(order_service_url, json=order_data, headers=headers) as response:
                if response.status != 201:
                    error = await response.text()
                    logger.error(f"Order service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to create order"
                    )
                
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to order service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in create_order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.post("/payment", response_model=PaymentResponse, summary="Process payment")
async def process_payment(
    order_id: str,
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Process payment for an order. This is a mock implementation.
    In a real system, this would integrate with a payment gateway.
    For this demo, it always returns success.
    """
    # This is a mock implementation - it always returns success
    # In a real system, you would call a payment service and handle the response
    
    try:
        # Forward the payment request to the order service
        order_service_url = f"http://order:8003/api/v1/orders/{order_id}/payment"
        
        payment_data = {
            "payment_method": "stripe",  # Hardcoded for simplicity
            "customer_id": token["user_id"]
        }
        
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(order_service_url, json=payment_data, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Order service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to process payment"
                    )
                
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to order service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in process_payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )
    
    # Mock success response for the demo
    return {
        "success": True,
        "message": "Payment processed successfully",
        "order_id": order_id
    }

@router.get("/", summary="Get user orders")
async def get_user_orders(
    status: Optional[str] = Query(None, description="Filter by order status"),
    limit: int = Query(20, ge=1, le=100, description="Number of results to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Get all orders for the current user.
    """
    # Forward the request to the order service
    try:
        order_service_url = "http://order:8003/api/v1/orders/customer"
        
        params = {
            "limit": limit,
            "offset": offset
        }
        
        if status:
            params["status"] = status
            
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(order_service_url, params=params, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Order service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to retrieve orders"
                    )
                
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to order service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_user_orders: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/{order_id}", summary="Get order details")
async def get_order_details(
    order_id: str,
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Get details of a specific order.
    """
    # Forward the request to the order service
    try:
        order_service_url = f"http://order:8003/api/v1/orders/{order_id}"
        
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(order_service_url, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Order service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to retrieve order details"
                    )
                
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to order service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in get_order_details: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/{order_id}/tracking", summary="Track order")
async def track_order(
    order_id: str,
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Track the status and location of an order in real-time.
    """
    # Forward the request to the order service
    try:
        order_service_url = f"http://order:8003/api/v1/orders/{order_id}/tracking"
        
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(order_service_url, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Order service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to retrieve order tracking information"
                    )
                
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to order service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in track_order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.post("/{order_id}/cancel", summary="Cancel order")
async def cancel_order(
    order_id: str,
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Cancel an order if it has not been delivered yet.
    """
    # Forward the request to the order service
    try:
        order_service_url = f"http://order:8003/api/v1/orders/{order_id}/cancel"
        
        headers = {
            "Authorization": f"Bearer {token.get('raw_token', '')}"
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(order_service_url, headers=headers) as response:
                if response.status != 200:
                    error = await response.text()
                    logger.error(f"Order service error: {error}")
                    raise HTTPException(
                        status_code=response.status,
                        detail="Failed to cancel order"
                    )
                
                return await response.json()
    except aiohttp.ClientError as e:
        logger.error(f"Error connecting to order service: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Order service unavailable"
        )
    except Exception as e:
        logger.error(f"Unexpected error in cancel_order: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )