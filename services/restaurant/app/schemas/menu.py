from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

class CategoryBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    display_order: int = Field(0, ge=0)

class CategoryCreate(CategoryBase):
    pass

class CategoryUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

class CategoryResponse(CategoryBase):
    id: str
    restaurant_id: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class MenuItemBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    price: float = Field(..., ge=0)
    category_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_vegetarian: bool = False
    is_vegan: bool = False
    is_gluten_free: bool = False
    spice_level: Optional[int] = Field(None, ge=0, le=4)
    preparation_time: Optional[int] = Field(None, ge=1)  # in minutes
    calories: Optional[int] = Field(None, ge=0)
    allergens: Optional[List[str]] = None
    is_featured: bool = False
    display_order: int = Field(0, ge=0)

    @validator('price')
    def validate_price(cls, v):
        if v < 0:
            raise ValueError('Price must be a positive number')
        return round(v, 2)  # Round to 2 decimal places

class MenuItemCreate(MenuItemBase):
    pass

class MenuItemUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    price: Optional[float] = Field(None, ge=0)
    category_id: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    is_vegetarian: Optional[bool] = None
    is_vegan: Optional[bool] = None
    is_gluten_free: Optional[bool] = None
    spice_level: Optional[int] = Field(None, ge=0, le=4)
    preparation_time: Optional[int] = Field(None, ge=1)  # in minutes
    calories: Optional[int] = Field(None, ge=0)
    allergens: Optional[List[str]] = None
    is_available: Optional[bool] = None
    is_featured: Optional[bool] = None
    display_order: Optional[int] = Field(None, ge=0)

    @validator('price')
    def validate_price(cls, v):
        if v is not None and v < 0:
            raise ValueError('Price must be a positive number')
        if v is not None:
            return round(v, 2)  # Round to 2 decimal places
        return v

class MenuItemResponse(MenuItemBase):
    id: str
    restaurant_id: str
    is_available: bool
    created_at: datetime
    updated_at: datetime

class CustomizationGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    is_required: bool = False
    min_selections: int = Field(0, ge=0)
    max_selections: Optional[int] = None
    display_order: int = Field(0, ge=0)

    @validator('max_selections')
    def validate_max_selections(cls, v, values):
        if v is not None and 'min_selections' in values and v < values['min_selections']:
            raise ValueError('Max selections must be greater than or equal to min selections')
        return v

class CustomizationGroupCreate(CustomizationGroupBase):
    pass

class CustomizationGroupUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    is_required: Optional[bool] = None
    min_selections: Optional[int] = Field(None, ge=0)
    max_selections: Optional[int] = None
    display_order: Optional[int] = Field(None, ge=0)

    @validator('max_selections')
    def validate_max_selections(cls, v, values):
        if v is not None and 'min_selections' in values and values['min_selections'] is not None and v < values['min_selections']:
            raise ValueError('Max selections must be greater than or equal to min selections')
        return v

class CustomizationGroupResponse(CustomizationGroupBase):
    id: str
    menu_item_id: str

class CustomizationOptionBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = None
    price_adjustment: float = Field(0, ge=0)
    is_default: bool = False
    display_order: int = Field(0, ge=0)

    @validator('price_adjustment')
    def validate_price_adjustment(cls, v):
        return round(v, 2)  # Round to 2 decimal places

class CustomizationOptionCreate(CustomizationOptionBase):
    pass

class CustomizationOptionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    price_adjustment: Optional[float] = Field(None, ge=0)
    is_default: Optional[bool] = None
    display_order: Optional[int] = Field(None, ge=0)

    @validator('price_adjustment')
    def validate_price_adjustment(cls, v):
        if v is not None:
            return round(v, 2)  # Round to 2 decimal places
        return v

class CustomizationOptionResponse(CustomizationOptionBase):
    id: str
    group_id: str

class CustomizationGroupWithOptions(CustomizationGroupResponse):
    options: List[CustomizationOptionResponse]

class MenuItemWithCustomizations(MenuItemResponse):
    customization_groups: List[CustomizationGroupWithOptions]

class MenuCategoryWithItems(BaseModel):
    category: CategoryResponse
    items: List[MenuItemResponse]

class FullMenuResponse(BaseModel):
    restaurant_id: str
    categories: List[MenuCategoryWithItems]