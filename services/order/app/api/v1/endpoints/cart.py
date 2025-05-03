from fastapi import APIRouter, Depends, HTTPException, Path, status
from typing import Dict, Any, Optional

from app.core.auth import get_current_user
from app.models.cart import CartRepository
from app.schemas.cart import (
    CartUpdateRequest, CartAddItemRequest, CartUpdateItemRequest,
    CartResponse
)

router = APIRouter()
cart_repository = CartRepository()

@router.get("", response_model=CartResponse)
async def get_cart(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Get the current user's shopping cart.
    
    This endpoint allows a user to retrieve their current shopping cart. If the user
    doesn't have a cart, null is returned.
    """
    cart = await cart_repository.get_user_cart(current_user["id"])
    
    if not cart:
        return {
            "restaurant_id": "",
            "items": [],
            "subtotal": 0,
            "updated_at": None
        }
    
    return cart

@router.post("", response_model=CartResponse)
async def update_cart(
    cart_data: CartUpdateRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update the current user's shopping cart.
    
    This endpoint allows a user to update their current shopping cart with a new set
    of items. If the user already has a cart, it will be replaced.
    """
    cart = await cart_repository.update_user_cart(
        user_id=current_user["id"],
        restaurant_id=cart_data.restaurant_id,
        items=[item.dict() for item in cart_data.items],
        subtotal=cart_data.subtotal
    )
    
    return cart

@router.post("/item", response_model=CartResponse)
async def add_item_to_cart(
    item_data: CartAddItemRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Add an item to the current user's shopping cart.
    
    This endpoint allows a user to add an item to their current shopping cart. If the user
    doesn't have a cart, a new one will be created. If the user has a cart with items from
    a different restaurant, the cart will be cleared before adding the new item.
    """
    cart = await cart_repository.add_item_to_cart(
        user_id=current_user["id"],
        restaurant_id=item_data.restaurant_id,
        item=item_data.item.dict()
    )
    
    return cart

@router.put("/item/{menu_item_id}", response_model=Optional[CartResponse])
async def update_item_quantity(
    item_data: CartUpdateItemRequest,
    menu_item_id: str = Path(..., description="The ID of the menu item to update"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Update the quantity of an item in the current user's shopping cart.
    
    This endpoint allows a user to update the quantity of an item in their current shopping cart.
    If the quantity is 0, the item will be removed from the cart. If the cart becomes empty,
    it will be deleted.
    """
    cart = await cart_repository.update_item_quantity(
        user_id=current_user["id"],
        menu_item_id=menu_item_id,
        quantity=item_data.quantity
    )
    
    if not cart:
        return {
            "restaurant_id": "",
            "items": [],
            "subtotal": 0,
            "updated_at": None
        }
    
    return cart

@router.delete("/item/{menu_item_id}", response_model=Optional[CartResponse])
async def remove_item_from_cart(
    menu_item_id: str = Path(..., description="The ID of the menu item to remove"),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Remove an item from the current user's shopping cart.
    
    This endpoint allows a user to remove an item from their current shopping cart.
    If the cart becomes empty, it will be deleted.
    """
    cart = await cart_repository.remove_item_from_cart(
        user_id=current_user["id"],
        menu_item_id=menu_item_id
    )
    
    if not cart:
        return {
            "restaurant_id": "",
            "items": [],
            "subtotal": 0,
            "updated_at": None
        }
    
    return cart

@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_cart(
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """
    Clear the current user's shopping cart.
    
    This endpoint allows a user to clear their current shopping cart.
    """
    await cart_repository.clear_cart(current_user["id"])
    return None