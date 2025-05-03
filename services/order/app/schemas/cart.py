from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import datetime

class CartItemRequest(BaseModel):
    """Cart item creation or update request."""
    menu_item_id: str = Field(..., description="The ID of the menu item")
    menu_item_name: str = Field(..., description="The name of the menu item")
    quantity: int = Field(..., gt=0, description="The quantity of the item")
    unit_price: float = Field(..., gt=0, description="The unit price of the item")
    special_instructions: Optional[str] = Field(None, description="Special instructions for the item")
    customizations: Optional[Dict[str, Any]] = Field(None, description="Customizations for the item")

class CartUpdateRequest(BaseModel):
    """Cart update request."""
    restaurant_id: str = Field(..., description="The ID of the restaurant")
    items: List[CartItemRequest] = Field(..., min_items=1, description="The items in the cart")
    subtotal: float = Field(..., gt=0, description="The subtotal of the cart")

class CartAddItemRequest(BaseModel):
    """Add item to cart request."""
    restaurant_id: str = Field(..., description="The ID of the restaurant")
    item: CartItemRequest = Field(..., description="The item to add to the cart")

class CartUpdateItemRequest(BaseModel):
    """Update cart item quantity request."""
    quantity: int = Field(..., ge=0, description="The new quantity of the item (0 to remove)")

class CartResponse(BaseModel):
    """Cart response model."""
    restaurant_id: str
    items: List[Dict[str, Any]]
    subtotal: float
    updated_at: Optional[str] = None

class CartItemResponse(BaseModel):
    """Cart item response model."""
    menu_item_id: str
    menu_item_name: str
    quantity: int
    unit_price: float
    subtotal: float
    special_instructions: Optional[str] = None
    customizations: Optional[Dict[str, Any]] = None