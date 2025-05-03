from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime

class CustomerProfileBase(BaseModel):
    dietary_preferences: List[str] = []
    favorite_cuisines: List[str] = []

class CustomerProfileUpdate(CustomerProfileBase):
    pass

class CustomerProfileResponse(CustomerProfileBase):
    user_id: str
    average_rating: Optional[float] = None
    created_at: datetime
    updated_at: datetime

class FavoriteRestaurantResponse(BaseModel):
    id: str
    restaurant_id: str
    restaurant_name: str
    cuisine_type: List[str]
    price_range: int
    average_rating: float
    created_at: datetime

class FavoriteMenuItemResponse(BaseModel):
    id: str
    menu_item_id: str
    menu_item_name: str
    restaurant_id: str
    restaurant_name: str
    price: float
    image_url: Optional[str] = None
    created_at: datetime

class NotificationSettingsBase(BaseModel):
    email_notifications: bool = True
    sms_notifications: bool = True
    push_notifications: bool = True
    order_updates: bool = True
    promotional_emails: bool = True
    new_restaurant_alerts: bool = False
    special_offers: bool = True

class NotificationSettingsUpdate(NotificationSettingsBase):
    pass

class NotificationSettingsResponse(NotificationSettingsBase):
    user_id: str
    created_at: datetime
    updated_at: datetime