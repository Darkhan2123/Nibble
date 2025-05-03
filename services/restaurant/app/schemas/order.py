from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class OrderStatus(str, Enum):
    PLACED = "placed"
    CONFIRMED = "confirmed"
    PREPARING = "preparing"
    READY_FOR_PICKUP = "ready_for_pickup"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    PICKED_UP = "picked_up"
    CANCELLED = "cancelled"

class OrderItem(BaseModel):
    id: str
    menu_item_id: str
    menu_item_name: str
    quantity: int
    unit_price: float
    subtotal: float
    special_instructions: Optional[str] = None
    customizations: Optional[Dict[str, Any]] = None

class OrderUpdateRequest(BaseModel):
    status: OrderStatus
    notes: Optional[str] = None

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = [
            "confirmed", "preparing", "ready_for_pickup", 
            "out_for_delivery", "picked_up", "cancelled"
        ]
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v

class OrderResponse(BaseModel):
    id: str
    order_number: str
    customer_id: str
    restaurant_id: str
    driver_id: Optional[str] = None
    status: OrderStatus
    subtotal: float
    tax: float
    delivery_fee: float
    tip: Optional[float] = None
    promo_discount: Optional[float] = None
    total_amount: float
    payment_method: Optional[str] = None
    payment_status: str
    delivery_address_id: Optional[str] = None
    special_instructions: Optional[str] = None
    estimated_delivery_time: Optional[datetime] = None
    restaurant_preparation_time: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItem]

class OrderListResponse(BaseModel):
    items: List[OrderResponse]
    total: int
    limit: int
    offset: int

class OrderHistoryParams(BaseModel):
    start_date: Optional[str] = None  # ISO format date string
    end_date: Optional[str] = None    # ISO format date string
    limit: int = Field(100, ge=1, le=1000)
    offset: int = Field(0, ge=0)

class OrderStatisticsResponse(BaseModel):
    total_orders: int
    completed_orders: int
    cancelled_orders: int
    average_preparation_time: float
    average_order_value: float
    total_revenue: float
    period: str  # 'day', 'week', 'month', 'year'