import logging
import uuid
from typing import Dict, List, Optional, Any

from app.core.database import get_connection, create_transaction
from app.core.maps import geocode_address

logger = logging.getLogger(__name__)

class AddressRepository:
    """Repository for address-related database operations."""
    
    async def create_address(
        self,
        user_id: str,
        address_line1: str,
        city: str,
        state: str,
        postal_code: str,
        address_type: str,
        address_line2: Optional[str] = None,
        country: str = "Казахстан",
        is_default: bool = False,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
    ) -> Dict[str, Any]:
        """
        Create a new address for a user.
        
        If latitude and longitude are not provided, they will be geocoded from the address.
        """
        # If not provided, geocode the address to get latitude and longitude
        if latitude is None or longitude is None:
            full_address = f"{address_line1}, {city}, {state}, {postal_code}, {country}"
            if address_line2:
                full_address = f"{address_line1}, {address_line2}, {city}, {state}, {postal_code}, {country}"
                
            try:
                geocode_result = await geocode_address(full_address)
                latitude = geocode_result['latitude']
                longitude = geocode_result['longitude']
            except Exception as e:
                logger.warning(f"Failed to geocode address: {e}")
                # Default to 0,0 if geocoding fails
                latitude = 0
                longitude = 0
        
        # Prepare the insert query
        async with get_connection() as conn:
            # Start a transaction
            tr = conn.transaction()
            await tr.start()
            
            try:
                # If this is the first address for the user and is_default is not specified,
                # make it the default address
                if not is_default:
                    # Check if user has any other addresses
                    existing_addresses = await conn.fetch(
                        "SELECT id FROM user_service.addresses WHERE user_id = $1",
                        user_id
                    )
                    
                    if not existing_addresses:
                        is_default = True
                
                # If this address is being set as default, unset any existing default addresses
                if is_default:
                    await conn.execute(
                        "UPDATE user_service.addresses SET is_default = FALSE WHERE user_id = $1",
                        user_id
                    )
                
                # Insert the new address
                insert_query = """
                INSERT INTO user_service.addresses 
                (user_id, address_line1, address_line2, city, state, postal_code, country, 
                 location, is_default, address_type)
                VALUES 
                ($1, $2, $3, $4, $5, $6, $7, ST_SetSRID(ST_Point($8, $9), 4326)::geography, $10, $11)
                RETURNING id, user_id, address_line1, address_line2, city, state, postal_code, country, 
                          ST_X(location::geometry) as longitude, ST_Y(location::geometry) as latitude, 
                          is_default, address_type, created_at, updated_at
                """
                
                row = await conn.fetchrow(
                    insert_query,
                    user_id, address_line1, address_line2, city, state, postal_code, country,
                    longitude, latitude, is_default, address_type
                )
                
                # Commit the transaction
                await tr.commit()
                
                # Format the result
                address_dict = dict(row)
                address_dict['location'] = {
                    'latitude': address_dict.pop('latitude'),
                    'longitude': address_dict.pop('longitude')
                }
                
                return address_dict
            except Exception as e:
                # Rollback the transaction
                await tr.rollback()
                logger.error(f"Error creating address: {e}")
                raise
    
    async def get_address_by_id(self, address_id: str, user_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get an address by ID.
        
        Args:
            address_id: The ID of the address to retrieve.
            user_id: If provided, ensures the address belongs to this user.
        
        Returns:
            The address data if found, None otherwise.
        """
        query = """
        SELECT id, user_id, address_line1, address_line2, city, state, postal_code, country,
               ST_X(location::geometry) as longitude, ST_Y(location::geometry) as latitude,
               is_default, address_type, created_at, updated_at
        FROM user_service.addresses
        WHERE id = $1
        """
        
        params = [address_id]
        
        if user_id:
            query += " AND user_id = $2"
            params.append(user_id)
        
        async with get_connection() as conn:
            try:
                row = await conn.fetchrow(query, *params)
                if row:
                    address_dict = dict(row)
                    address_dict['location'] = {
                        'latitude': address_dict.pop('latitude'),
                        'longitude': address_dict.pop('longitude')
                    }
                    return address_dict
                return None
            except Exception as e:
                logger.error(f"Error getting address by ID: {e}")
                raise
    
    async def get_addresses_by_user_id(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Get all addresses for a user.
        
        Args:
            user_id: The ID of the user to get addresses for.
        
        Returns:
            A list of addresses for the user.
        """
        query = """
        SELECT id, user_id, address_line1, address_line2, city, state, postal_code, country,
               ST_X(location::geometry) as longitude, ST_Y(location::geometry) as latitude,
               is_default, address_type, created_at, updated_at
        FROM user_service.addresses
        WHERE user_id = $1
        ORDER BY is_default DESC, created_at DESC
        """
        
        async with get_connection() as conn:
            try:
                rows = await conn.fetch(query, user_id)
                addresses = []
                
                for row in rows:
                    address_dict = dict(row)
                    address_dict['location'] = {
                        'latitude': address_dict.pop('latitude'),
                        'longitude': address_dict.pop('longitude')
                    }
                    addresses.append(address_dict)
                
                return addresses
            except Exception as e:
                logger.error(f"Error getting addresses by user ID: {e}")
                raise
    
    async def update_address(
        self,
        address_id: str,
        update_data: Dict[str, Any],
        user_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Update an address.
        
        Args:
            address_id: The ID of the address to update.
            update_data: A dictionary of fields to update.
            user_id: If provided, ensures the address belongs to this user.
        
        Returns:
            The updated address data if found and updated, None otherwise.
        """
        async with get_connection() as conn:
            tr = conn.transaction()
            await tr.start()
            
            try:
                # First, check if the address exists and belongs to the user
                check_query = "SELECT user_id FROM user_service.addresses WHERE id = $1"
                params = [address_id]
                
                if user_id:
                    check_query += " AND user_id = $2"
                    params.append(user_id)
                
                address_user_id = await conn.fetchval(check_query, *params)
                
                if not address_user_id:
                    await tr.rollback()
                    return None
                
                # If user_id was not provided, use the one from the address
                if not user_id:
                    user_id = address_user_id
                
                # Build the SET clause and parameters list
                set_clauses = []
                params = []
                
                # Handle standard fields
                fields = [
                    'address_line1', 'address_line2', 'city', 'state', 
                    'postal_code', 'country', 'is_default', 'address_type'
                ]
                
                for i, field in enumerate(fields):
                    if field in update_data:
                        set_clauses.append(f"{field} = ${len(params) + 1}")
                        params.append(update_data[field])
                
                # Handle location separately
                latitude = update_data.get('latitude')
                longitude = update_data.get('longitude')
                
                if latitude is not None and longitude is not None:
                    set_clauses.append(f"location = ST_SetSRID(ST_Point(${len(params) + 1}, ${len(params) + 2}), 4326)::geography")
                    params.extend([longitude, latitude])
                elif 'address_line1' in update_data or 'city' in update_data or 'state' in update_data or 'postal_code' in update_data:
                    # If address components changed but no coordinates provided, try to geocode
                    # First, get the current address data
                    current_address = await self.get_address_by_id(address_id)
                    
                    if current_address:
                        # Create a new address with updated fields
                        address_line1 = update_data.get('address_line1', current_address['address_line1'])
                        address_line2 = update_data.get('address_line2', current_address['address_line2'])
                        city = update_data.get('city', current_address['city'])
                        state = update_data.get('state', current_address['state'])
                        postal_code = update_data.get('postal_code', current_address['postal_code'])
                        country = update_data.get('country', current_address['country'])
                        
                        full_address = f"{address_line1}, {city}, {state}, {postal_code}, {country}"
                        if address_line2:
                            full_address = f"{address_line1}, {address_line2}, {city}, {state}, {postal_code}, {country}"
                        
                        try:
                            geocode_result = await geocode_address(full_address)
                            longitude = geocode_result['longitude']
                            latitude = geocode_result['latitude']
                            
                            set_clauses.append(f"location = ST_SetSRID(ST_Point(${len(params) + 1}, ${len(params) + 2}), 4326)::geography")
                            params.extend([longitude, latitude])
                        except Exception as e:
                            logger.warning(f"Failed to geocode updated address: {e}")
                
                # If there's nothing to update, return the current address
                if not set_clauses:
                    await tr.rollback()
                    return await self.get_address_by_id(address_id, user_id)
                
                # Add updated_at timestamp
                set_clauses.append("updated_at = CURRENT_TIMESTAMP")
                
                # If this address is being set as default, unset any existing default addresses
                if 'is_default' in update_data and update_data['is_default']:
                    await conn.execute(
                        "UPDATE user_service.addresses SET is_default = FALSE WHERE user_id = $1 AND id != $2",
                        user_id, address_id
                    )
                
                # Build the final query
                query = f"""
                UPDATE user_service.addresses
                SET {", ".join(set_clauses)}
                WHERE id = $${len(params) + 1}
                RETURNING id, user_id, address_line1, address_line2, city, state, postal_code, country,
                      ST_X(location::geometry) as longitude, ST_Y(location::geometry) as latitude,
                      is_default, address_type, created_at, updated_at
                """
                
                params.append(address_id)
                
                row = await conn.fetchrow(query, *params)
                
                # Commit the transaction
                await tr.commit()
                
                if row:
                    address_dict = dict(row)
                    address_dict['location'] = {
                        'latitude': address_dict.pop('latitude'),
                        'longitude': address_dict.pop('longitude')
                    }
                    return address_dict
                
                return None
            except Exception as e:
                # Rollback the transaction
                await tr.rollback()
                logger.error(f"Error updating address: {e}")
                raise
    
    async def delete_address(self, address_id: str, user_id: Optional[str] = None) -> bool:
        """
        Delete an address.
        
        Args:
            address_id: The ID of the address to delete.
            user_id: If provided, ensures the address belongs to this user.
        
        Returns:
            True if the address was deleted, False otherwise.
        """
        query = "DELETE FROM user_service.addresses WHERE id = $1"
        params = [address_id]
        
        if user_id:
            query += " AND user_id = $2"
            params.append(user_id)
        
        async with get_connection() as conn:
            try:
                result = await conn.execute(query, *params)
                
                # If this was a default address and was successfully deleted,
                # set another address as default if available
                if result == "DELETE 1" and user_id:
                    # Find if user has any other addresses
                    remaining_addresses = await conn.fetch(
                        "SELECT id FROM user_service.addresses WHERE user_id = $1 ORDER BY created_at DESC",
                        user_id
                    )
                    
                    if remaining_addresses:
                        # Set the most recently created address as default
                        await conn.execute(
                            "UPDATE user_service.addresses SET is_default = TRUE WHERE id = $1",
                            remaining_addresses[0]['id']
                        )
                
                return result == "DELETE 1"
            except Exception as e:
                logger.error(f"Error deleting address: {e}")
                raise