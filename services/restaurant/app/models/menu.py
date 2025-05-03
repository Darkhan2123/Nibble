import logging
import uuid
from typing import Dict, List, Optional, Any
import asyncpg

from app.core.database import get_connection, transaction, fetch_one, fetch_all, execute
from app.core.redis import (
    cache_menu_items, get_cached_menu_items, invalidate_menu_cache,
    get_cached_restaurant
)

logger = logging.getLogger(__name__)

class MenuRepository:
    """Repository for menu-related database operations."""
    
    async def create_category(
        self,
        restaurant_id: str,
        name: str,
        description: Optional[str] = None,
        display_order: int = 0
    ) -> Dict[str, Any]:
        """Create a new menu category."""
        query = """
        INSERT INTO restaurant_service.menu_categories (
            id, restaurant_id, name, description, display_order
        ) VALUES (
            $1, $2, $3, $4, $5
        )
        RETURNING *
        """
        
        try:
            category_id = str(uuid.uuid4())
            return await fetch_one(
                query,
                category_id,
                restaurant_id,
                name,
                description,
                display_order
            )
        except asyncpg.UniqueViolationError:
            logger.error(f"Category name already exists for restaurant: {restaurant_id}")
            raise ValueError(f"Category name '{name}' already exists for this restaurant")
        except Exception as e:
            logger.error(f"Error creating category: {e}")
            raise
    
    async def get_category(self, category_id: str) -> Optional[Dict[str, Any]]:
        """Get a menu category by ID."""
        query = """
        SELECT * FROM restaurant_service.menu_categories
        WHERE id = $1
        """
        
        return await fetch_one(query, category_id)
    
    async def get_categories_by_restaurant(
        self,
        restaurant_id: str
    ) -> List[Dict[str, Any]]:
        """Get all menu categories for a restaurant."""
        query = """
        SELECT * FROM restaurant_service.menu_categories
        WHERE restaurant_id = $1 AND is_active = TRUE
        ORDER BY display_order
        """
        
        return await fetch_all(query, restaurant_id)
    
    async def update_category(
        self,
        category_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a menu category."""
        # Only allow updating certain fields
        allowed_fields = {"name", "description", "display_order", "is_active"}
        
        # Filter out fields that are not allowed to be updated
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not filtered_data:
            return await self.get_category(category_id)
        
        # Construct the SQL SET clause
        set_clauses = []
        values = []
        params_index = 1
        
        for field, value in filtered_data.items():
            set_clauses.append(f"{field} = ${params_index}")
            values.append(value)
            params_index += 1
        
        set_clause = ", ".join(set_clauses)
        
        # Construct the full query
        query = f"""
        UPDATE restaurant_service.menu_categories
        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
        WHERE id = ${params_index}
        RETURNING *
        """
        
        values.append(category_id)
        
        try:
            return await fetch_one(query, *values)
        except asyncpg.UniqueViolationError:
            logger.error(f"Category name already exists for this restaurant")
            raise ValueError("Category name already exists for this restaurant")
        except Exception as e:
            logger.error(f"Error updating category: {e}")
            raise
    
    async def delete_category(self, category_id: str) -> bool:
        """Delete a menu category."""
        # In a real application, you would want to check if there are menu items
        # in this category first and handle them appropriately
        query = """
        DELETE FROM restaurant_service.menu_categories
        WHERE id = $1
        """
        
        result = await execute(query, category_id)
        return "DELETE 1" in result
    
    async def create_menu_item(
        self,
        restaurant_id: str,
        name: str,
        price: float,
        category_id: Optional[str] = None,
        description: Optional[str] = None,
        image_url: Optional[str] = None,
        is_vegetarian: bool = False,
        is_vegan: bool = False,
        is_gluten_free: bool = False,
        spice_level: Optional[int] = None,
        preparation_time: Optional[int] = None,
        calories: Optional[int] = None,
        allergens: Optional[List[str]] = None,
        is_featured: bool = False,
        display_order: int = 0
    ) -> Dict[str, Any]:
        """Create a new menu item."""
        query = """
        INSERT INTO restaurant_service.menu_items (
            id, restaurant_id, category_id, name, description, price, image_url,
            is_vegetarian, is_vegan, is_gluten_free, spice_level, preparation_time,
            calories, allergens, is_featured, display_order
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16
        )
        RETURNING *
        """
        
        try:
            menu_item_id = str(uuid.uuid4())
            return await fetch_one(
                query,
                menu_item_id,
                restaurant_id,
                category_id,
                name,
                description,
                price,
                image_url,
                is_vegetarian,
                is_vegan,
                is_gluten_free,
                spice_level,
                preparation_time,
                calories,
                allergens,
                is_featured,
                display_order
            )
        except Exception as e:
            logger.error(f"Error creating menu item: {e}")
            raise
    
    async def get_menu_item(self, menu_item_id: str) -> Optional[Dict[str, Any]]:
        """Get a menu item by ID."""
        query = """
        SELECT * FROM restaurant_service.menu_items
        WHERE id = $1
        """
        
        return await fetch_one(query, menu_item_id)
    
    async def get_menu_items_by_restaurant(
        self,
        restaurant_id: str,
        category_id: Optional[str] = None,
        include_unavailable: bool = False
    ) -> List[Dict[str, Any]]:
        """Get all menu items for a restaurant, optionally filtered by category."""
        conditions = ["restaurant_id = $1"]
        params = [restaurant_id]
        param_index = 2
        
        if category_id:
            conditions.append(f"category_id = ${param_index}")
            params.append(category_id)
            param_index += 1
        
        if not include_unavailable:
            conditions.append("is_available = TRUE")
        
        where_clause = " AND ".join(conditions)
        
        query = f"""
        SELECT * FROM restaurant_service.menu_items
        WHERE {where_clause}
        ORDER BY display_order, name
        """
        
        return await fetch_all(query, *params)
    
    async def update_menu_item(
        self,
        menu_item_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """Update a menu item."""
        # Only allow updating certain fields
        allowed_fields = {
            "category_id", "name", "description", "price", "image_url",
            "is_vegetarian", "is_vegan", "is_gluten_free", "spice_level",
            "preparation_time", "calories", "allergens", "is_available",
            "is_featured", "display_order"
        }
        
        # Filter out fields that are not allowed to be updated
        filtered_data = {k: v for k, v in update_data.items() if k in allowed_fields}
        
        if not filtered_data:
            return await self.get_menu_item(menu_item_id)
        
        # Construct the SQL SET clause
        set_clauses = []
        values = []
        params_index = 1
        
        for field, value in filtered_data.items():
            set_clauses.append(f"{field} = ${params_index}")
            values.append(value)
            params_index += 1
        
        set_clause = ", ".join(set_clauses)
        
        # Construct the full query
        query = f"""
        UPDATE restaurant_service.menu_items
        SET {set_clause}, updated_at = CURRENT_TIMESTAMP
        WHERE id = ${params_index}
        RETURNING *
        """
        
        values.append(menu_item_id)
        
        try:
            return await fetch_one(query, *values)
        except Exception as e:
            logger.error(f"Error updating menu item: {e}")
            raise
    
    async def delete_menu_item(self, menu_item_id: str) -> bool:
        """Delete a menu item."""
        # In a real application, you would want to check if there are orders
        # that reference this menu item first and handle them appropriately
        query = """
        DELETE FROM restaurant_service.menu_items
        WHERE id = $1
        """
        
        result = await execute(query, menu_item_id)
        return "DELETE 1" in result
    
    async def create_customization_group(
        self,
        menu_item_id: str,
        name: str,
        description: Optional[str] = None,
        is_required: bool = False,
        min_selections: int = 0,
        max_selections: Optional[int] = None,
        display_order: int = 0
    ) -> Dict[str, Any]:
        """Create a new customization group."""
        query = """
        INSERT INTO restaurant_service.customization_groups (
            id, menu_item_id, name, description, is_required,
            min_selections, max_selections, display_order
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, $8
        )
        RETURNING *
        """
        
        try:
            group_id = str(uuid.uuid4())
            return await fetch_one(
                query,
                group_id,
                menu_item_id,
                name,
                description,
                is_required,
                min_selections,
                max_selections,
                display_order
            )
        except Exception as e:
            logger.error(f"Error creating customization group: {e}")
            raise
    
    async def get_customization_groups(
        self,
        menu_item_id: str
    ) -> List[Dict[str, Any]]:
        """Get all customization groups for a menu item."""
        query = """
        SELECT * FROM restaurant_service.customization_groups
        WHERE menu_item_id = $1
        ORDER BY display_order
        """
        
        return await fetch_all(query, menu_item_id)
    
    async def create_customization_option(
        self,
        group_id: str,
        name: str,
        description: Optional[str] = None,
        price_adjustment: float = 0.0,
        is_default: bool = False,
        display_order: int = 0
    ) -> Dict[str, Any]:
        """Create a new customization option."""
        query = """
        INSERT INTO restaurant_service.customization_options (
            id, group_id, name, description, price_adjustment,
            is_default, display_order
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7
        )
        RETURNING *
        """
        
        try:
            option_id = str(uuid.uuid4())
            return await fetch_one(
                query,
                option_id,
                group_id,
                name,
                description,
                price_adjustment,
                is_default,
                display_order
            )
        except Exception as e:
            logger.error(f"Error creating customization option: {e}")
            raise
    
    async def get_customization_options(
        self,
        group_id: str
    ) -> List[Dict[str, Any]]:
        """Get all customization options for a group."""
        query = """
        SELECT * FROM restaurant_service.customization_options
        WHERE group_id = $1
        ORDER BY display_order
        """
        
        return await fetch_all(query, group_id)
    
    async def get_menu_item_with_customizations(
        self,
        menu_item_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a menu item with all its customization options."""
        # Get the menu item
        menu_item = await self.get_menu_item(menu_item_id)
        
        if not menu_item:
            return None
        
        # Get the customization groups
        groups = await self.get_customization_groups(menu_item_id)
        
        # Get the options for each group
        for group in groups:
            group["options"] = await self.get_customization_options(group["id"])
        
        menu_item["customization_groups"] = groups
        return menu_item
    
    async def get_full_menu(
        self,
        restaurant_id: str,
        include_unavailable: bool = False
    ) -> Dict[str, Any]:
        """Get the full menu structure for a restaurant."""
        # Only check cache for standard menu (not including unavailable items)
        if not include_unavailable:
            logger.debug(f"Checking cache for restaurant {restaurant_id} menu")
            cached_menu = await get_cached_menu_items(restaurant_id)
            if cached_menu:
                logger.info(f"Using cached menu for restaurant {restaurant_id}")
                return cached_menu

        # If cache miss or requesting with unavailable items, fetch from database
        logger.debug(f"Cache miss or include_unavailable={include_unavailable}, fetching menu from database")
        
        # Get all categories
        categories = await self.get_categories_by_restaurant(restaurant_id)
        
        # Get all menu items
        menu_items = await self.get_menu_items_by_restaurant(
            restaurant_id,
            include_unavailable=include_unavailable
        )
        
        # Organize menu items by category
        menu_by_category = {}
        
        # First, create an entry for each category
        for category in categories:
            category_id = category["id"]
            menu_by_category[category_id] = {
                "category": category,
                "items": []
            }
        
        # Add a category for uncategorized items
        menu_by_category["uncategorized"] = {
            "category": {
                "id": "uncategorized",
                "name": "Uncategorized",
                "display_order": 999
            },
            "items": []
        }
        
        # Add menu items to their respective categories
        for item in menu_items:
            category_id = item.get("category_id")
            if category_id and category_id in menu_by_category:
                menu_by_category[category_id]["items"].append(item)
            else:
                menu_by_category["uncategorized"]["items"].append(item)
        
        # Convert the dictionary to a list and sort by category display order
        menu = []
        for category_data in menu_by_category.values():
            if category_data["items"]:  # Only include categories with items
                menu.append(category_data)
        
        menu.sort(key=lambda x: x["category"]["display_order"])
        
        menu_data = {
            "restaurant_id": restaurant_id,
            "categories": menu
        }
        
        # Cache the result, but only for standard menu (not including unavailable items)
        if not include_unavailable:
            logger.info(f"Caching menu for restaurant {restaurant_id}")
            await cache_menu_items(restaurant_id, menu_data)
        
        return menu_data