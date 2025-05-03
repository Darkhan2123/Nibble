from fastapi import APIRouter, Depends, HTTPException, status
from typing import Dict, Any, List
import logging

from app.core.auth import validate_token
from app.models.address import AddressRepository
from app.schemas.address import AddressCreate, AddressUpdate, AddressResponse
from app.core.maps import geocode_address

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/", response_model=List[AddressResponse])
async def list_addresses(token: Dict[str, Any] = Depends(validate_token)):
    """
    List all addresses for the current user.
    """
    address_repo = AddressRepository()
    
    try:
        addresses = await address_repo.get_addresses_by_user_id(token["user_id"])
        return addresses
    except Exception as e:
        logger.error(f"Error listing addresses: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve addresses"
        )

@router.post("/", response_model=AddressResponse, status_code=status.HTTP_201_CREATED)
async def create_address(
    address: AddressCreate, 
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Create a new address for the current user.
    """
    address_repo = AddressRepository()
    
    # If coordinates are not provided, geocode the address
    if not address.latitude or not address.longitude:
        try:
            full_address = f"{address.address_line1}, {address.city}, {address.state}, {address.postal_code}, {address.country}"
            if address.address_line2:
                full_address = f"{address.address_line1}, {address.address_line2}, {address.city}, {address.state}, {address.postal_code}, {address.country}"
            
            geocode_result = await geocode_address(full_address)
            address.latitude = geocode_result['latitude']
            address.longitude = geocode_result['longitude']
        except Exception as e:
            logger.warning(f"Failed to geocode address: {e}")
            # Continue with creation even if geocoding fails
    
    try:
        created_address = await address_repo.create_address(
            user_id=token["user_id"],
            address_line1=address.address_line1,
            address_line2=address.address_line2,
            city=address.city,
            state=address.state,
            postal_code=address.postal_code,
            country=address.country,
            is_default=address.is_default,
            address_type=address.address_type,
            latitude=address.latitude,
            longitude=address.longitude
        )
        return created_address
    except Exception as e:
        logger.error(f"Error creating address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create address"
        )

@router.get("/{address_id}", response_model=AddressResponse)
async def get_address(
    address_id: str, 
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Get an address by ID.
    """
    address_repo = AddressRepository()
    
    try:
        address = await address_repo.get_address_by_id(address_id, token["user_id"])
        
        if not address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found"
            )
        
        return address
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve address"
        )

@router.put("/{address_id}", response_model=AddressResponse)
async def update_address(
    address_id: str, 
    address_update: AddressUpdate, 
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Update an address.
    """
    address_repo = AddressRepository()
    
    # First, check if the address exists and belongs to the user
    existing_address = await address_repo.get_address_by_id(address_id, token["user_id"])
    
    if not existing_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found or doesn't belong to you"
        )
    
    # Convert Pydantic model to dict, excluding None values
    update_data = address_update.dict(exclude_unset=True)
    
    # If location-related fields are updated but no coordinates are provided,
    # try to geocode the address
    address_fields_updated = any(field in update_data for field in 
                              ['address_line1', 'address_line2', 'city', 'state', 'postal_code', 'country'])
    coordinates_provided = 'latitude' in update_data and 'longitude' in update_data
    
    if address_fields_updated and not coordinates_provided:
        try:
            # Create full address with updated and existing fields
            address_line1 = update_data.get('address_line1', existing_address['address_line1'])
            address_line2 = update_data.get('address_line2', existing_address['address_line2'])
            city = update_data.get('city', existing_address['city'])
            state = update_data.get('state', existing_address['state'])
            postal_code = update_data.get('postal_code', existing_address['postal_code'])
            country = update_data.get('country', existing_address['country'])
            
            full_address = f"{address_line1}, {city}, {state}, {postal_code}, {country}"
            if address_line2:
                full_address = f"{address_line1}, {address_line2}, {city}, {state}, {postal_code}, {country}"
            
            geocode_result = await geocode_address(full_address)
            update_data['latitude'] = geocode_result['latitude']
            update_data['longitude'] = geocode_result['longitude']
        except Exception as e:
            logger.warning(f"Failed to geocode updated address: {e}")
            # Continue with update even if geocoding fails
    
    try:
        updated_address = await address_repo.update_address(
            address_id=address_id,
            update_data=update_data,
            user_id=token["user_id"]
        )
        
        if not updated_address:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found or update failed"
            )
        
        return updated_address
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update address"
        )

@router.delete("/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_address(
    address_id: str, 
    token: Dict[str, Any] = Depends(validate_token)
):
    """
    Delete an address.
    
    If the address is the default address, another address will be set as default.
    """
    address_repo = AddressRepository()
    
    # Check if the address exists and belongs to the user
    existing_address = await address_repo.get_address_by_id(address_id, token["user_id"])
    
    if not existing_address:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Address not found or doesn't belong to you"
        )
    
    # Get all user addresses to ensure they'll have at least one after deletion
    user_addresses = await address_repo.get_addresses_by_user_id(token["user_id"])
    
    if len(user_addresses) <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete the only address. At least one address is required."
        )
    
    try:
        deleted = await address_repo.delete_address(address_id, token["user_id"])
        
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Address not found or deletion failed"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting address: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete address"
        )