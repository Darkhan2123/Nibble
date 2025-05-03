from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum

class DeliveryStatus(str, Enum):
    READY_FOR_PICKUP = "ready_for_pickup"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"

class DeliveryStatusUpdate(BaseModel):
    status: DeliveryStatus
    notes: Optional[str] = None
    location: Optional[Dict[str, float]] = None

    @validator('status')
    def validate_status(cls, v):
        valid_statuses = ['out_for_delivery', 'delivered', 'cancelled']
        if v not in valid_statuses:
            raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        return v
    
    @validator('location')
    def validate_location(cls, v):
        if v is None:
            return v
        if 'latitude' not in v or 'longitude' not in v:
            raise ValueError("Location must include latitude and longitude")
        if v['latitude'] < -90 or v['latitude'] > 90:
            raise ValueError("Latitude must be between -90 and 90")
        if v['longitude'] < -180 or v['longitude'] > 180:
            raise ValueError("Longitude must be between -180 and 180")
        return v

class OrderItem(BaseModel):
    id: str
    menu_item_id: str
    menu_item_name: str
    quantity: int
    unit_price: float
    subtotal: float
    special_instructions: Optional[str] = None
    customizations: Optional[Dict[str, Any]] = None

class DeliveryResponse(BaseModel):
    id: str
    order_number: str
    customer_id: str
    restaurant_id: str
    driver_id: str
    status: str
    subtotal: float
    tax: float
    delivery_fee: float
    tip: Optional[float] = None
    total_amount: float
    delivery_address_id: str
    special_instructions: Optional[str] = None
    estimated_delivery_time: Optional[datetime] = None
    actual_delivery_time: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    items: List[OrderItem]

class DeliveryRouteResponse(BaseModel):
    order_id: str
    driver_id: str
    route_to_restaurant: Dict[str, Any]
    route_to_customer: Dict[str, Any]
    total_distance: float
    estimated_pickup_time: float
    estimated_delivery_time: float
    total_time: float
    avoid_tolls: Optional[bool] = False

class DeliveryListResponse(BaseModel):
    items: List[DeliveryResponse]
    total: int
    limit: int
    offset: int

class DeliverySummary(BaseModel):
    total_deliveries: int
    completed_deliveries: int
    cancelled_deliveries: int
    total_distance: float
    total_earnings: float
    average_rating: float

class LocationPoint(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    recorded_at: datetime
    status: str

class DeliveryLocationHistory(BaseModel):
    order_id: str
    driver_id: str
    locations: List[LocationPoint]
    total_locations: int

class DeliveryLocationResponse(BaseModel):
    order_id: str
    status: str
    current_location: Dict[str, float]
    updated_at: datetime