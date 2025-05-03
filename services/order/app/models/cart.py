import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from app.core.redis import get_cart, update_cart, delete_cart

logger = logging.getLogger(__name__)

class CartRepository:
    """Repository for cart-related operations."""
    
    async def get_user_cart(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get a user's shopping cart."""
        cart = await get_cart(user_id)
        
        if not cart:
            return None
        
        return cart
    
    async def update_user_cart(
        self,
        user_id: str,
        restaurant_id: str,
        items: List[Dict[str, Any]],
        subtotal: float
    ) -> Dict[str, Any]:
        """Update or create a user's shopping cart."""
        cart = {
            "restaurant_id": restaurant_id,
            "items": items,
            "subtotal": subtotal,
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await update_cart(user_id, cart)
        
        return cart
    
    async def add_item_to_cart(
        self,
        user_id: str,
        restaurant_id: str,
        item: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add an item to a user's shopping cart."""
        # Get existing cart
        existing_cart = await get_cart(user_id)
        
        # If cart exists but has items from a different restaurant, clear it
        if existing_cart and existing_cart.get("restaurant_id") != restaurant_id:
            existing_cart = {
                "restaurant_id": restaurant_id,
                "items": [],
                "subtotal": 0
            }
        
        # If cart doesn't exist, create a new one
        if not existing_cart:
            existing_cart = {
                "restaurant_id": restaurant_id,
                "items": [],
                "subtotal": 0
            }
        
        # Check if item already exists in cart
        items = existing_cart.get("items", [])
        found = False
        
        for i, cart_item in enumerate(items):
            if cart_item.get("menu_item_id") == item.get("menu_item_id"):
                # If the item has customizations, treat it as a different item
                if self._compare_customizations(cart_item, item):
                    # Update quantity and subtotal for existing item
                    items[i]["quantity"] = cart_item.get("quantity", 0) + item.get("quantity", 1)
                    items[i]["subtotal"] = round(items[i]["quantity"] * items[i].get("unit_price", 0), 2)
                    found = True
                    break
        
        # If item not found in cart, add it
        if not found:
            # Calculate item subtotal
            item["subtotal"] = round(item.get("quantity", 1) * item.get("unit_price", 0), 2)
            items.append(item)
        
        # Recalculate cart subtotal
        subtotal = sum(item.get("subtotal", 0) for item in items)
        
        # Update cart
        cart = {
            "restaurant_id": restaurant_id,
            "items": items,
            "subtotal": round(subtotal, 2),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await update_cart(user_id, cart)
        
        return cart
    
    async def update_item_quantity(
        self,
        user_id: str,
        menu_item_id: str,
        quantity: int
    ) -> Optional[Dict[str, Any]]:
        """Update the quantity of an item in the cart."""
        # Get existing cart
        existing_cart = await get_cart(user_id)
        
        if not existing_cart:
            return None
        
        # Update item quantity or remove if quantity is 0
        items = existing_cart.get("items", [])
        found = False
        
        for i, item in enumerate(items):
            if item.get("menu_item_id") == menu_item_id:
                if quantity <= 0:
                    # Remove item from cart
                    items.pop(i)
                else:
                    # Update quantity and subtotal
                    items[i]["quantity"] = quantity
                    items[i]["subtotal"] = round(quantity * items[i].get("unit_price", 0), 2)
                found = True
                break
        
        if not found:
            return existing_cart
        
        # If cart is empty after removing item, delete cart
        if not items:
            await delete_cart(user_id)
            return None
        
        # Recalculate cart subtotal
        subtotal = sum(item.get("subtotal", 0) for item in items)
        
        # Update cart
        cart = {
            "restaurant_id": existing_cart.get("restaurant_id"),
            "items": items,
            "subtotal": round(subtotal, 2),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        await update_cart(user_id, cart)
        
        return cart
    
    async def remove_item_from_cart(
        self,
        user_id: str,
        menu_item_id: str
    ) -> Optional[Dict[str, Any]]:
        """Remove an item from the cart."""
        return await self.update_item_quantity(user_id, menu_item_id, 0)
    
    async def clear_cart(self, user_id: str) -> bool:
        """Clear a user's shopping cart."""
        return await delete_cart(user_id)
    
    def _compare_customizations(self, item1: Dict[str, Any], item2: Dict[str, Any]) -> bool:
        """Compare customizations to see if two items are the same."""
        # If one has customizations and the other doesn't, they're different
        if ("customizations" in item1) != ("customizations" in item2):
            return False
        
        # If neither has customizations, they're the same
        if "customizations" not in item1 and "customizations" not in item2:
            return True
        
        # Compare customizations
        return item1.get("customizations") == item2.get("customizations")