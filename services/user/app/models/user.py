import uuid
from typing import Optional, Dict, List, Any
import asyncpg
import logging
from app.core.database import get_connection, create_transaction

logger = logging.getLogger(__name__)

class UserRepository:
    """Repository for user-related database operations."""
    
    async def create_user(self, password: str, **kwargs) -> Dict[str, Any]:
        """
        Create a new user in the database.
        
        Args:
            password: The plaintext password to hash
            **kwargs: User data including email, phone_number, first_name, last_name, etc.
            
        Returns:
            Dictionary with user data including the generated ID.
        """
        from app.core.auth import get_password_hash
        
        # Hash the password
        password_hash = get_password_hash(password)
        
        async with get_connection() as conn:
            # Start a transaction
            tr = conn.transaction()
            await tr.start()
            
            try:
                # Insert the user and get the ID
                insert_query = """
                INSERT INTO user_service.users 
                (email, phone_number, password_hash, first_name, last_name, date_of_birth, profile_picture_url)
                VALUES ($1, $2, $3, $4, $5, $6, $7)
                RETURNING id, email, phone_number, first_name, last_name, date_of_birth, profile_picture_url, 
                          is_active, created_at, updated_at
                """
                
                user = await conn.fetchrow(
                    insert_query,
                    kwargs.get('email'),
                    kwargs.get('phone_number'),
                    password_hash,
                    kwargs.get('first_name'),
                    kwargs.get('last_name'),
                    kwargs.get('date_of_birth'),
                    kwargs.get('profile_picture_url')
                )
                
                # Convert to dictionary
                user_dict = dict(user)
                # Convert UUID to string for JSON serialization
                user_dict['id'] = str(user_dict['id'])
                
                # Add default user role (customer)
                await conn.execute(
                    "INSERT INTO user_service.user_roles (user_id, role_id) VALUES ($1, 1)",
                    user_dict['id']
                )
                
                # Create customer profile
                await conn.execute(
                    "INSERT INTO user_service.customer_profiles (user_id) VALUES ($1)",
                    user_dict['id']
                )
                
                # Create notification settings
                await conn.execute(
                    "INSERT INTO user_service.notification_settings (user_id) VALUES ($1)",
                    user_dict['id']
                )
                
                # Commit transaction
                await tr.commit()
                return user_dict
            except Exception as e:
                # Rollback transaction
                await tr.rollback()
                logger.error(f"Error creating user: {e}")
                raise
    
    async def get_user_by_email(self, email: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by email address.
        
        Args:
            email: The email to look up.
            
        Returns:
            User data dictionary or None if not found.
        """
        query = """
        SELECT u.id, u.email, u.phone_number, u.password_hash, u.first_name, u.last_name, 
               u.date_of_birth, u.profile_picture_url, u.is_active, 
               u.created_at, u.updated_at
        FROM user_service.users u
        WHERE u.email = $1
        """
        
        async with get_connection() as conn:
            try:
                row = await conn.fetchrow(query, email)
                if row:
                    user_dict = dict(row)
                    # Convert UUID to string for JSON serialization
                    user_dict['id'] = str(user_dict['id'])
                    return user_dict
                return None
            except Exception as e:
                logger.error(f"Error getting user by email: {e}")
                raise
        
    async def get_user_by_phone(self, phone_number: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by phone number.
        
        Args:
            phone_number: The phone number to look up.
            
        Returns:
            User data dictionary or None if not found.
        """
        query = """
        SELECT u.id, u.email, u.phone_number, u.password_hash, u.first_name, u.last_name, 
               u.date_of_birth, u.profile_picture_url, u.is_active, 
               u.created_at, u.updated_at
        FROM user_service.users u
        WHERE u.phone_number = $1
        """
        
        async with get_connection() as conn:
            try:
                row = await conn.fetchrow(query, phone_number)
                if row:
                    user_dict = dict(row)
                    # Convert UUID to string for JSON serialization
                    user_dict['id'] = str(user_dict['id'])
                    return user_dict
                return None
            except Exception as e:
                logger.error(f"Error getting user by phone: {e}")
                raise
    
    async def get_user_by_id(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a user by ID.
        
        Args:
            user_id: The user ID to look up.
            
        Returns:
            User data dictionary or None if not found.
        """
        query = """
        SELECT u.id, u.email, u.phone_number, u.first_name, u.last_name, 
               u.date_of_birth, u.profile_picture_url, u.is_active, 
               u.created_at, u.updated_at
        FROM user_service.users u
        WHERE u.id = $1
        """
        
        async with get_connection() as conn:
            try:
                row = await conn.fetchrow(query, user_id)
                if row:
                    user_dict = dict(row)
                    # Convert UUID to string for JSON serialization
                    user_dict['id'] = str(user_dict['id'])
                    return user_dict
                return None
            except Exception as e:
                logger.error(f"Error getting user by ID: {e}")
                raise
    
    async def get_user_roles(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get roles for a user.
        
        Args:
            user_id: The user ID to get roles for.
            
        Returns:
            List of role dictionaries with at least a name field.
        """
        query = """
        SELECT r.id, r.name, r.description
        FROM user_service.roles r
        JOIN user_service.user_roles ur ON r.id = ur.role_id
        WHERE ur.user_id = $1
        """
        
        async with get_connection() as conn:
            try:
                roles = await conn.fetch(query, user_id)
                return [dict(role) for role in roles]
            except Exception as e:
                logger.error(f"Error getting user roles: {e}")
                raise
    
    async def update_user(self, user_id: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Update user data.
        
        Args:
            user_id: The user ID to update.
            **kwargs: Fields to update.
            
        Returns:
            Updated user data or None if user not found.
        """
        # Build the SET clause for the update query
        set_clauses = []
        params = [user_id]  # First parameter is user_id
        
        for i, (key, value) in enumerate(kwargs.items(), start=2):
            if key != 'password':  # Handle password separately
                set_clauses.append(f"{key} = ${i}")
                params.append(value)
        
        # If there's nothing to update, return early
        if not set_clauses:
            return await self.get_user_by_id(user_id)
        
        # Add updated_at timestamp
        set_clauses.append("updated_at = CURRENT_TIMESTAMP")
        
        # Build the final query
        query = f"""
        UPDATE user_service.users
        SET {", ".join(set_clauses)}
        WHERE id = $1
        RETURNING id, email, phone_number, first_name, last_name, 
                 date_of_birth, profile_picture_url, is_active, 
                 created_at, updated_at
        """
        
        async with get_connection() as conn:
            try:
                row = await conn.fetchrow(query, *params)
                if row:
                    user_dict = dict(row)
                    # Convert UUID to string for JSON serialization
                    user_dict['id'] = str(user_dict['id'])
                    return user_dict
                return None
            except Exception as e:
                logger.error(f"Error updating user: {e}")
                raise
    
    async def update_password(self, user_id: str, new_password: str) -> bool:
        """
        Update a user's password.
        
        Args:
            user_id: The ID of the user to update.
            new_password: The new plaintext password to hash and store.
            
        Returns:
            True if successful, False otherwise.
        """
        from app.core.auth import get_password_hash
        
        password_hash = get_password_hash(new_password)
        
        query = """
        UPDATE user_service.users
        SET password_hash = $2, updated_at = CURRENT_TIMESTAMP
        WHERE id = $1
        """
        
        async with get_connection() as conn:
            try:
                result = await conn.execute(query, user_id, password_hash)
                return result == "UPDATE 1"
            except Exception as e:
                logger.error(f"Error updating password: {e}")
                raise
    
    async def delete_user(self, user_id: str) -> bool:
        """
        Delete a user.
        
        Args:
            user_id: The user ID to delete.
            
        Returns:
            True if user was deleted, False otherwise.
        """
        query = "DELETE FROM user_service.users WHERE id = $1"
        
        async with get_connection() as conn:
            try:
                result = await conn.execute(query, user_id)
                return result == "DELETE 1"
            except Exception as e:
                logger.error(f"Error deleting user: {e}")
                raise
                
    async def add_user_role(self, user_id: str, role_name: str) -> bool:
        """
        Add a role to a user.
        
        Args:
            user_id: The user ID.
            role_name: The name of the role to add.
            
        Returns:
            True if successful, False otherwise.
        """
        # First, get the role ID
        role_query = "SELECT id FROM user_service.roles WHERE name = $1"
        
        async with get_connection() as conn:
            try:
                role_id = await conn.fetchval(role_query, role_name)
                if not role_id:
                    logger.error(f"Role not found: {role_name}")
                    return False
                
                # Add the role
                result = await conn.execute(
                    "INSERT INTO user_service.user_roles (user_id, role_id) VALUES ($1, $2) ON CONFLICT DO NOTHING",
                    user_id, role_id
                )
                return True
            except Exception as e:
                logger.error(f"Error adding user role: {e}")
                raise
                
    async def remove_user_role(self, user_id: str, role_name: str) -> bool:
        """
        Remove a role from a user.
        
        Args:
            user_id: The user ID.
            role_name: The name of the role to remove.
            
        Returns:
            True if successful, False otherwise.
        """
        # First, get the role ID
        role_query = "SELECT id FROM user_service.roles WHERE name = $1"
        
        async with get_connection() as conn:
            try:
                role_id = await conn.fetchval(role_query, role_name)
                if not role_id:
                    logger.error(f"Role not found: {role_name}")
                    return False
                
                # Remove the role
                result = await conn.execute(
                    "DELETE FROM user_service.user_roles WHERE user_id = $1 AND role_id = $2",
                    user_id, role_id
                )
                return result == "DELETE 1"
            except Exception as e:
                logger.error(f"Error removing user role: {e}")
                raise