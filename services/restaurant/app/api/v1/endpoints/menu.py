from fastapi import APIRouter, Depends, HTTPException, status, Query, Path, UploadFile, File, Form
from typing import Dict, List, Optional, Any
import logging
import json
from pydantic import parse_obj_as

from app.core.auth import validate_token, has_role, restaurant_owner_or_admin
from app.models.menu import MenuRepository
from app.models.restaurant import RestaurantRepository
from app.schemas.menu import (
    CategoryCreate, CategoryUpdate, CategoryResponse,
    MenuItemCreate, MenuItemUpdate, MenuItemResponse, MenuItemWithCustomizations,
    CustomizationGroupCreate, CustomizationGroupUpdate, CustomizationGroupResponse, CustomizationGroupWithOptions,
    CustomizationOptionCreate, CustomizationOptionUpdate, CustomizationOptionResponse,
    FullMenuResponse
)
from app.core.kafka import (
    publish_menu_item_created, publish_menu_item_updated, publish_menu_item_deleted
)
from app.core.redis import invalidate_menu_cache

logger = logging.getLogger(__name__)

router = APIRouter()

# Categories endpoints
@router.post("/categories", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CategoryCreate,
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Create a new menu category for the current user's restaurant.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    menu_repo = MenuRepository()
    
    # Get the user's restaurant
    restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    try:
        new_category = await menu_repo.create_category(
            restaurant_id=restaurant["id"],
            name=category.name,
            description=category.description,
            display_order=category.display_order
        )
        
        # Invalidate menu cache
        await invalidate_menu_cache(restaurant["id"])
        
        logger.info(f"Category created with ID: {new_category['id']}")
        
        return new_category
        
    except ValueError as e:
        logger.error(f"Error creating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error creating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/categories", response_model=List[CategoryResponse])
async def get_restaurant_categories(
    restaurant_id: str,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get all categories for a restaurant.
    """
    menu_repo = MenuRepository()
    
    categories = await menu_repo.get_categories_by_restaurant(restaurant_id)
    
    return categories

@router.get("/categories/{category_id}", response_model=CategoryResponse)
async def get_category(
    category_id: str,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get a category by ID.
    """
    menu_repo = MenuRepository()
    
    category = await menu_repo.get_category(category_id)
    
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    return category

@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    category: CategoryUpdate,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Update a category. Only the owner of the restaurant can do this.
    """
    menu_repo = MenuRepository()
    
    # Get the category to check ownership
    existing_category = await menu_repo.get_category(category_id)
    
    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if user is authorized to update this category
    await restaurant_owner_or_admin(
        restaurant_id=existing_category["restaurant_id"]
    )(user_info)
    
    try:
        updated_category = await menu_repo.update_category(
            category_id=category_id,
            update_data=category.dict(exclude_unset=True)
        )
        
        # Invalidate menu cache
        await invalidate_menu_cache(existing_category["restaurant_id"])
        
        logger.info(f"Category updated with ID: {updated_category['id']}")
        
        return updated_category
        
    except ValueError as e:
        logger.error(f"Error updating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Unexpected error updating category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.delete("/categories/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: str,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Delete a category. Only the owner of the restaurant can do this.
    """
    menu_repo = MenuRepository()
    
    # Get the category to check ownership
    existing_category = await menu_repo.get_category(category_id)
    
    if not existing_category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if user is authorized to delete this category
    await restaurant_owner_or_admin(
        restaurant_id=existing_category["restaurant_id"]
    )(user_info)
    
    try:
        success = await menu_repo.delete_category(category_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete category"
            )
        
        # Invalidate menu cache
        await invalidate_menu_cache(existing_category["restaurant_id"])
        
        logger.info(f"Category deleted with ID: {category_id}")
        
    except Exception as e:
        logger.error(f"Unexpected error deleting category: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

# Menu items endpoints
@router.post("/items", response_model=MenuItemResponse, status_code=status.HTTP_201_CREATED)
async def create_menu_item(
    menu_item: MenuItemCreate,
    user_info: Dict[str, Any] = Depends(has_role("restaurant"))
):
    """
    Create a new menu item for the current user's restaurant.
    """
    user_id = user_info["user_id"]
    restaurant_repo = RestaurantRepository()
    menu_repo = MenuRepository()
    
    # Get the user's restaurant
    restaurant = await restaurant_repo.get_restaurant_by_user_id(user_id)
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant not found for this user"
        )
    
    # If category_id is provided, check if it belongs to this restaurant
    if menu_item.category_id:
        category = await menu_repo.get_category(menu_item.category_id)
        if not category or category["restaurant_id"] != restaurant["id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID"
            )
    
    try:
        new_item = await menu_repo.create_menu_item(
            restaurant_id=restaurant["id"],
            name=menu_item.name,
            price=menu_item.price,
            category_id=menu_item.category_id,
            description=menu_item.description,
            image_url=menu_item.image_url,
            is_vegetarian=menu_item.is_vegetarian,
            is_vegan=menu_item.is_vegan,
            is_gluten_free=menu_item.is_gluten_free,
            spice_level=menu_item.spice_level,
            preparation_time=menu_item.preparation_time,
            calories=menu_item.calories,
            allergens=menu_item.allergens,
            is_featured=menu_item.is_featured,
            display_order=menu_item.display_order
        )
        
        # Invalidate menu cache
        await invalidate_menu_cache(restaurant["id"])
        
        # Publish menu item created event
        await publish_menu_item_created({
            "menu_item_id": new_item["id"],
            "restaurant_id": restaurant["id"],
            "name": new_item["name"],
            "price": new_item["price"],
            "category_id": new_item.get("category_id")
        })
        
        logger.info(f"Menu item created with ID: {new_item['id']}")
        
        return new_item
        
    except Exception as e:
        logger.error(f"Unexpected error creating menu item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/items", response_model=List[MenuItemResponse])
async def get_restaurant_menu_items(
    restaurant_id: str,
    category_id: Optional[str] = None,
    include_unavailable: bool = False,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get all menu items for a restaurant, optionally filtered by category.
    """
    menu_repo = MenuRepository()
    
    menu_items = await menu_repo.get_menu_items_by_restaurant(
        restaurant_id=restaurant_id,
        category_id=category_id,
        include_unavailable=include_unavailable
    )
    
    return menu_items

@router.get("/items/{item_id}", response_model=MenuItemWithCustomizations)
async def get_menu_item(
    item_id: str,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get a menu item by ID, including its customization options.
    """
    menu_repo = MenuRepository()
    
    menu_item = await menu_repo.get_menu_item_with_customizations(item_id)
    
    if not menu_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    return menu_item

@router.put("/items/{item_id}", response_model=MenuItemResponse)
async def update_menu_item(
    item_id: str,
    menu_item: MenuItemUpdate,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Update a menu item. Only the owner of the restaurant can do this.
    """
    menu_repo = MenuRepository()
    
    # Get the menu item to check ownership
    existing_item = await menu_repo.get_menu_item(item_id)
    
    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    # Check if user is authorized to update this menu item
    await restaurant_owner_or_admin(
        restaurant_id=existing_item["restaurant_id"]
    )(user_info)
    
    # If category_id is provided, check if it belongs to this restaurant
    if menu_item.category_id:
        category = await menu_repo.get_category(menu_item.category_id)
        if not category or category["restaurant_id"] != existing_item["restaurant_id"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid category ID"
            )
    
    try:
        updated_item = await menu_repo.update_menu_item(
            menu_item_id=item_id,
            update_data=menu_item.dict(exclude_unset=True)
        )
        
        # Invalidate menu cache
        await invalidate_menu_cache(existing_item["restaurant_id"])
        
        # Publish menu item updated event
        await publish_menu_item_updated({
            "menu_item_id": updated_item["id"],
            "restaurant_id": updated_item["restaurant_id"],
            "name": updated_item["name"],
            "price": updated_item["price"],
            "category_id": updated_item.get("category_id"),
            "is_available": updated_item["is_available"]
        })
        
        logger.info(f"Menu item updated with ID: {updated_item['id']}")
        
        return updated_item
        
    except Exception as e:
        logger.error(f"Unexpected error updating menu item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.delete("/items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_menu_item(
    item_id: str,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Delete a menu item. Only the owner of the restaurant can do this.
    """
    menu_repo = MenuRepository()
    
    # Get the menu item to check ownership
    existing_item = await menu_repo.get_menu_item(item_id)
    
    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    # Check if user is authorized to delete this menu item
    await restaurant_owner_or_admin(
        restaurant_id=existing_item["restaurant_id"]
    )(user_info)
    
    try:
        success = await menu_repo.delete_menu_item(item_id)
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete menu item"
            )
        
        # Invalidate menu cache
        await invalidate_menu_cache(existing_item["restaurant_id"])
        
        # Publish menu item deleted event
        await publish_menu_item_deleted(
            restaurant_id=existing_item["restaurant_id"],
            menu_item_id=item_id
        )
        
        logger.info(f"Menu item deleted with ID: {item_id}")
        
    except Exception as e:
        logger.error(f"Unexpected error deleting menu item: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

# Customization groups endpoints
@router.post("/items/{item_id}/customization-groups", response_model=CustomizationGroupResponse)
async def create_customization_group(
    item_id: str,
    group: CustomizationGroupCreate,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Create a customization group for a menu item.
    """
    menu_repo = MenuRepository()
    
    # Get the menu item to check ownership
    existing_item = await menu_repo.get_menu_item(item_id)
    
    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    # Check if user is authorized to update this menu item
    await restaurant_owner_or_admin(
        restaurant_id=existing_item["restaurant_id"]
    )(user_info)
    
    try:
        new_group = await menu_repo.create_customization_group(
            menu_item_id=item_id,
            name=group.name,
            description=group.description,
            is_required=group.is_required,
            min_selections=group.min_selections,
            max_selections=group.max_selections,
            display_order=group.display_order
        )
        
        # Invalidate menu cache
        await invalidate_menu_cache(existing_item["restaurant_id"])
        
        logger.info(f"Customization group created with ID: {new_group['id']}")
        
        return new_group
        
    except Exception as e:
        logger.error(f"Unexpected error creating customization group: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/items/{item_id}/customization-groups", response_model=List[CustomizationGroupWithOptions])
async def get_customization_groups(
    item_id: str,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get all customization groups for a menu item.
    """
    menu_repo = MenuRepository()
    
    # Check if menu item exists
    existing_item = await menu_repo.get_menu_item(item_id)
    
    if not existing_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Menu item not found"
        )
    
    groups = await menu_repo.get_customization_groups(item_id)
    
    # Get options for each group
    result = []
    for group in groups:
        options = await menu_repo.get_customization_options(group["id"])
        group_with_options = {**group, "options": options}
        result.append(group_with_options)
    
    return result

# Customization options endpoints
@router.post("/customization-groups/{group_id}/options", response_model=CustomizationOptionResponse)
async def create_customization_option(
    group_id: str,
    option: CustomizationOptionCreate,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Create a customization option for a group.
    """
    menu_repo = MenuRepository()
    
    # Get the group to check ownership
    existing_group = await menu_repo.get_customization_groups(group_id)
    
    if not existing_group:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customization group not found"
        )
    
    # Get the menu item to check ownership
    menu_item = await menu_repo.get_menu_item(existing_group[0]["menu_item_id"])
    
    # Check if user is authorized to update this menu item
    await restaurant_owner_or_admin(
        restaurant_id=menu_item["restaurant_id"]
    )(user_info)
    
    try:
        new_option = await menu_repo.create_customization_option(
            group_id=group_id,
            name=option.name,
            description=option.description,
            price_adjustment=option.price_adjustment,
            is_default=option.is_default,
            display_order=option.display_order
        )
        
        # Invalidate menu cache
        await invalidate_menu_cache(menu_item["restaurant_id"])
        
        logger.info(f"Customization option created with ID: {new_option['id']}")
        
        return new_option
        
    except Exception as e:
        logger.error(f"Unexpected error creating customization option: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred"
        )

@router.get("/full-menu/{restaurant_id}", response_model=FullMenuResponse)
async def get_full_menu(
    restaurant_id: str,
    include_unavailable: bool = False,
    user_info: Dict[str, Any] = Depends(validate_token)
):
    """
    Get the full menu structure for a restaurant.
    Uses Redis caching to improve performance for frequently accessed menus.
    """
    menu_repo = MenuRepository()
    
    # The get_full_menu method now includes Redis caching logic
    menu = await menu_repo.get_full_menu(
        restaurant_id=restaurant_id,
        include_unavailable=include_unavailable
    )
    
    return menu