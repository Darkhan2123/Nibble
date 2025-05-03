from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, UUID4, validator
from decimal import Decimal
import uuid

class OrderItemRequest(BaseModel):
    """Order item creation request."""
    menu_item_id: str = Field(..., description="The ID of the menu item")
    menu_item_name: str = Field(..., description="The name of the menu item")
    quantity: int = Field(..., gt=0, description="The quantity of the item")
    unit_price: float = Field(..., gt=0, description="The unit price of the item")
    special_instructions: Optional[str] = Field(None, description="Special instructions for the item")
    customizations: Optional[Dict[str, Any]] = Field(None, description="Customizations for the item")

class OrderCreateRequest(BaseModel):
    """Order creation request."""
    restaurant_id: str = Field(..., description="The ID of the restaurant")
    address_id: str = Field(..., description="The ID of the delivery address")
    items: List[OrderItemRequest] = Field(..., min_items=1, description="The items in the order")
    payment_method: str = Field(..., description="The payment method for the order")
    subtotal: float = Field(..., gt=0, description="The subtotal of the order")
    delivery_fee: float = Field(..., ge=0, description="The delivery fee for the order")
    special_instructions: Optional[str] = Field(None, description="Special instructions for the order")
    promo_code: Optional[str] = Field(None, description="Promo code for the order")
    promo_discount: Optional[float] = Field(0, ge=0, description="Discount amount from promo code")

class OrderStatusUpdateRequest(BaseModel):
    """Order status update request."""
    status: str = Field(..., description="The new status of the order")
    notes: Optional[str] = Field(None, description="Notes about the status change")

class OrderPaymentUpdateRequest(BaseModel):
    """Order payment update request."""
    payment_status: str = Field(..., description="The new payment status of the order")
    payment_id: Optional[str] = Field(None, description="The payment ID from the payment processor")

class OrderDriverAssignRequest(BaseModel):
    """Order driver assignment request."""
    driver_id: str = Field(..., description="The ID of the driver to assign to the order")

class OrderEstimatedTimeUpdateRequest(BaseModel):
    """Order estimated delivery time update request."""
    estimated_delivery_time: datetime = Field(..., description="The estimated delivery time")

class OrderTipUpdateRequest(BaseModel):
    """Order tip update request."""
    tip_amount: float = Field(..., ge=0, description="The tip amount for the order")

class OrderRatingRequest(BaseModel):
    """Order rating request."""
    food_rating: Optional[int] = Field(None, ge=1, le=5, description="Rating for the food (1-5)")
    delivery_rating: Optional[int] = Field(None, ge=1, le=5, description="Rating for the delivery (1-5)")
    review_text: Optional[str] = Field(None, description="Review text")
    
    @validator('food_rating', 'delivery_rating', pre=True, always=True)
    def validate_ratings(cls, v, values, **kwargs):
        """Validate that at least one rating is provided."""
        field_name = kwargs['field'].name
        
        # If this is food_rating and it's None, check if delivery_rating will be provided
        if field_name == 'food_rating' and v is None:
            # Can't check delivery_rating yet since it hasn't been validated
            return v
            
        # If this is delivery_rating and it's None, check if food_rating was provided
        if field_name == 'delivery_rating' and v is None:
            food_rating = values.get('food_rating')
            if food_rating is None:
                raise ValueError("At least one of food_rating or delivery_rating must be provided")
        
        return v

class OrderItem(BaseModel):
    """Order item model."""
    id: str
    order_id: str
    menu_item_id: str
    menu_item_name: str
    quantity: int
    unit_price: float
    subtotal: float
    special_instructions: Optional[str] = None
    customizations: Optional[Dict[str, Any]] = None
    created_at: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class OrderResponse(BaseModel):
    """Order response model."""
    id: str
    order_number: str
    customer_id: str
    restaurant_id: str
    status: str
    subtotal: float
    tax: float
    delivery_fee: float
    promo_discount: float
    tip: Optional[float] = None
    total_amount: float
    payment_method: str
    payment_status: str
    stripe_payment_id: Optional[str] = None
    delivery_address_id: str
    driver_id: Optional[str] = None
    estimated_delivery_time: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None
    special_instructions: Optional[str] = None
    cancellation_time: Optional[datetime] = None
    cancellation_reason: Optional[str] = None
    cancelled_by: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItem]
    
    class Config:
        orm_mode = True

class OrderStatusHistoryResponse(BaseModel):
    """Order status history response model."""
    id: str
    order_id: str
    status: str
    updated_by_user_id: str
    notes: Optional[str] = None
    created_at: datetime
    
    class Config:
        orm_mode = True

class OrderListResponse(BaseModel):
    """Order list response model."""
    orders: List[OrderResponse]
    total: int
    page: int
    limit: int
    
class OrderTrackingResponse(BaseModel):
    """Real-time order tracking response model."""
    order_id: str
    order_number: str
    customer_id: str
    restaurant_id: str
    status: str
    delivery_address_id: str
    driver_id: Optional[str] = None
    driver_location: Optional[Dict[str, float]] = None
    estimated_delivery_time: Optional[datetime] = None
    restaurant_location: Optional[Dict[str, float]] = None
    last_status_update: datetime
    is_location_available: bool
    eta_minutes: Optional[int] = None
    route_polyline: Optional[List[List[float]]] = None