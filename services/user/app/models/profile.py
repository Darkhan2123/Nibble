import logging
import uuid
from typing import Dict, List, Optional, Any

from app.core.database import get_connection, create_transaction

logger = logging.getLogger(__name__)

class ProfileRepository:
    """Repository for profile-related database operations."""
    
    async def get_customer_profile(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a customer profile by user ID.
        
        Args:
            user_id: The user ID to get the profile for.
            
        Returns:
            The customer profile data if found, None otherwise.
        """
        query = """
        SELECT user_id, dietary_preferences, favorite_cuisines, average_rating, stripe_customer_id,
               created_at, updated_at
        FROM user_service.customer_profiles
        WHERE user_id = $1
        """
        
        async with get_connection() as conn:
            try:
                row = await conn.fetchrow(query, user_id)
                if row:
                    profile_dict = dict(row)
                    
                    # Handle JSONB fields
                    if profile_dict.get('dietary_preferences') is None:
                        profile_dict['dietary_preferences'] = []
                    
                    if profile_dict.get('favorite_cuisines') is None:
                        profile_dict['favorite_cuisines'] = []
                    
                    return profile_dict
                
                # If no profile exists, create a default one
                return await self.create_customer_profile(user_id)
            except Exception as e:
                logger.error(f"Error getting customer profile: {e}")
                raise
    
    async def create_customer_profile(self, user_id: str) -> Dict[str, Any]:
        """
        Create a new customer profile for a user.
        
        Args:
            user_id: The user ID to create a profile for.
            
        Returns:
            The newly created customer profile data.
        """
        query = """
        INSERT INTO user_service.customer_profiles 
        (user_id, dietary_preferences, favorite_cuisines)
        VALUES ($1, $2, $3)
        ON CONFLICT (user_id) DO NOTHING
        RETURNING user_id, dietary_preferences, favorite_cuisines, average_rating, stripe_customer_id, 
                 created_at, updated_at
        """
        
        async with get_connection() as conn:
            try:
                # Start a transaction
                tr = conn.transaction()
                await tr.start()
                
                # Try to insert a new profile
                row = await conn.fetchrow(
                    query, 
                    user_id, 
                    '[]',  # Empty array for dietary preferences
                    '[]'   # Empty array for favorite cuisines
                )
                
                # If insert was successful, return it
                if row:
                    await tr.commit()
                    profile_dict = dict(row)
                    
                    # Ensure JSONB fields are converted to Python lists
                    profile_dict['dietary_preferences'] = profile_dict.get('dietary_preferences', [])
                    profile_dict['favorite_cuisines'] = profile_dict.get('favorite_cuisines', [])
                    
                    return profile_dict
                
                # If there was a conflict (profile already exists), fetch the existing one
                await tr.rollback()
                
                existing_profile = await conn.fetchrow(
                    """
                    SELECT user_id, dietary_preferences, favorite_cuisines, average_rating, stripe_customer_id,
                           created_at, updated_at
                    FROM user_service.customer_profiles
                    WHERE user_id = $1
                    """,
                    user_id
                )
                
                if existing_profile:
                    profile_dict = dict(existing_profile)
                    
                    # Ensure JSONB fields are converted to Python lists
                    profile_dict['dietary_preferences'] = profile_dict.get('dietary_preferences', [])
                    profile_dict['favorite_cuisines'] = profile_dict.get('favorite_cuisines', [])
                    
                    return profile_dict
                
                # If somehow we still don't have a profile, return a default one
                return {
                    "user_id": user_id,
                    "dietary_preferences": [],
                    "favorite_cuisines": [],
                    "average_rating": None,
                    "stripe_customer_id": None,
                    "created_at": None,
                    "updated_at": None
                }
            except Exception as e:
                # Ensure transaction is rolled back on error
                try:
                    await tr.rollback()
                except:
                    pass
                
                logger.error(f"Error creating customer profile: {e}")
                raise
    
    async def update_customer_profile(
        self,
        user_id: str,
        update_data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Update a customer profile.
        
        Args:
            user_id: The user ID to update the profile for.
            update_data: A dictionary of fields to update.
            
        Returns:
            The updated customer profile data if successful, None otherwise.
        """
        # Get the current profile to ensure it exists
        current_profile = await self.get_customer_profile(user_id)
        if not current_profile:
            return None
        
        # Build the set clause and parameters
        set_clauses = []
        params = [user_id]  # First parameter is always user_id
        
        # Fields that can be updated
        updateable_fields = {
            'dietary_preferences': 'jsonb',
            'favorite_cuisines': 'jsonb',
            'stripe_customer_id': 'text'
        }
        
        for field, field_type in updateable_fields.items():
            if field in update_data:
                if field_type == 'jsonb' and update_data[field] is not None:
                    # Handle JSONB arrays
                    set_clauses.append(f"{field} = ${len(params) + 1}::jsonb")
                    params.append(update_data[field])
                else:
                    set_clauses.append(f"{field} = ${len(params) + 1}")
                    params.append(update_data[field])
        
        # If there's nothing to update, return the current profile
        if not set_clauses:
            return current_profile
        
        # Add updated_at timestamp
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        
        # Build the final query
        query = f"""
        UPDATE user_service.customer_profiles
        SET {", ".join(set_clauses)}
        WHERE user_id = $1
        RETURNING user_id, dietary_preferences, favorite_cuisines, average_rating, stripe_customer_id,
                 created_at, updated_at
        """
        
        async with get_connection() as conn:
            try:
                row = await conn.fetchrow(query, *params)
                if row:
                    profile_dict = dict(row)
                    
                    # Ensure JSONB fields are converted to Python lists
                    profile_dict['dietary_preferences'] = profile_dict.get('dietary_preferences', [])
                    profile_dict['favorite_cuisines'] = profile_dict.get('favorite_cuisines', [])
                    
                    return profile_dict
                return None
            except Exception as e:
                logger.error(f"Error updating customer profile: {e}")
                raise
    
    async def get_notification_settings(self, user_id: str) -> Optional[Dict[str, bool]]:
        """
        Get notification settings for a user.
        
        Args:
            user_id: The user ID to get notification settings for.
            
        Returns:
            A dictionary of notification settings if found, None otherwise.
        """
        query = """
        SELECT user_id, email_notifications, sms_notifications, push_notifications,
               order_updates, promotional_emails, new_restaurant_alerts, special_offers,
               created_at, updated_at
        FROM user_service.notification_settings
        WHERE user_id = $1
        """
        
        async with get_connection() as conn:
            try:
                row = await conn.fetchrow(query, user_id)
                if row:
                    # Convert to dictionary and remove timestamps
                    settings_dict = dict(row)
                    settings_dict.pop('user_id', None)
                    settings_dict.pop('created_at', None)
                    settings_dict.pop('updated_at', None)
                    return settings_dict
                
                # If no settings exist, create default settings
                return await self.create_notification_settings(user_id)
            except Exception as e:
                logger.error(f"Error getting notification settings: {e}")
                raise
    
    async def create_notification_settings(self, user_id: str) -> Dict[str, bool]:
        """
        Create default notification settings for a user.
        
        Args:
            user_id: The user ID to create notification settings for.
            
        Returns:
            The default notification settings.
        """
        query = """
        INSERT INTO user_service.notification_settings
        (user_id, email_notifications, sms_notifications, push_notifications,
         order_updates, promotional_emails, new_restaurant_alerts, special_offers)
        VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
        ON CONFLICT (user_id) DO NOTHING
        RETURNING user_id, email_notifications, sms_notifications, push_notifications,
                  order_updates, promotional_emails, new_restaurant_alerts, special_offers
        """
        
        # Default settings
        default_settings = {
            'email_notifications': True,
            'sms_notifications': True,
            'push_notifications': True,
            'order_updates': True,
            'promotional_emails': True,
            'new_restaurant_alerts': False,
            'special_offers': True
        }
        
        async with get_connection() as conn:
            try:
                # Start a transaction
                tr = conn.transaction()
                await tr.start()
                
                # Try to insert new settings
                row = await conn.fetchrow(
                    query,
                    user_id,
                    default_settings['email_notifications'],
                    default_settings['sms_notifications'],
                    default_settings['push_notifications'],
                    default_settings['order_updates'],
                    default_settings['promotional_emails'],
                    default_settings['new_restaurant_alerts'],
                    default_settings['special_offers']
                )
                
                # If insert was successful, return the settings
                if row:
                    await tr.commit()
                    settings_dict = dict(row)
                    settings_dict.pop('user_id', None)
                    return settings_dict
                
                # If there was a conflict (settings already exist), fetch the existing ones
                await tr.rollback()
                
                existing_settings = await conn.fetchrow(
                    """
                    SELECT user_id, email_notifications, sms_notifications, push_notifications,
                           order_updates, promotional_emails, new_restaurant_alerts, special_offers
                    FROM user_service.notification_settings
                    WHERE user_id = $1
                    """,
                    user_id
                )
                
                if existing_settings:
                    settings_dict = dict(existing_settings)
                    settings_dict.pop('user_id', None)
                    return settings_dict
                
                # If we still don't have settings, return the defaults
                return default_settings
            except Exception as e:
                # Ensure transaction is rolled back on error
                try:
                    await tr.rollback()
                except:
                    pass
                
                logger.error(f"Error creating notification settings: {e}")
                raise
    
    async def update_notification_settings(
        self,
        user_id: str,
        settings: Dict[str, bool]
    ) -> Optional[Dict[str, bool]]:
        """
        Update a user's notification settings.
        
        Args:
            user_id: The user ID to update notification settings for.
            settings: A dictionary of notification settings to update.
            
        Returns:
            The updated notification settings if successful, None otherwise.
        """
        # Get current settings to ensure they exist
        current_settings = await self.get_notification_settings(user_id)
        if not current_settings:
            return None
        
        # Build the SET clause and parameters
        set_clauses = []
        params = [user_id]  # First parameter is always user_id
        
        # Fields that can be updated
        updateable_fields = [
            'email_notifications',
            'sms_notifications',
            'push_notifications',
            'order_updates',
            'promotional_emails',
            'new_restaurant_alerts',
            'special_offers'
        ]
        
        for field in updateable_fields:
            if field in settings:
                set_clauses.append(f"{field} = ${len(params) + 1}")
                params.append(settings[field])
        
        # If there's nothing to update, return the current settings
        if not set_clauses:
            return current_settings
        
        # Add updated_at timestamp
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        
        # Build the final query
        query = f"""
        UPDATE user_service.notification_settings
        SET {", ".join(set_clauses)}
        WHERE user_id = $1
        RETURNING user_id, email_notifications, sms_notifications, push_notifications,
                  order_updates, promotional_emails, new_restaurant_alerts, special_offers
        """
        
        async with get_connection() as conn:
            try:
                row = await conn.fetchrow(query, *params)
                if row:
                    settings_dict = dict(row)
                    settings_dict.pop('user_id', None)
                    return settings_dict
                return None
            except Exception as e:
                logger.error(f"Error updating notification settings: {e}")
                raise