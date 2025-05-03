import httpx
import logging
from typing import Dict, Any, Optional, List

from app.core.config import settings

logger = logging.getLogger(__name__)

# Client for making requests to other services
class ServiceClient:
    """HTTP client for making requests to other services."""
    
    def __init__(self, base_url: str, timeout: float = 10.0):
        """Initialize the service client."""
        self.base_url = base_url
        self.timeout = timeout
    
    async def get(
        self,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make a GET request to the service."""
        url = f"{self.base_url}{path}"
        
        request_headers = headers or {}
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(
                    url,
                    params=params,
                    headers=request_headers
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise
    
    async def post(
        self,
        path: str,
        json: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make a POST request to the service."""
        url = f"{self.base_url}{path}"
        
        request_headers = headers or {}
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=json,
                    headers=request_headers
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise
    
    async def put(
        self,
        path: str,
        json: Dict[str, Any],
        headers: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make a PUT request to the service."""
        url = f"{self.base_url}{path}"
        
        request_headers = headers or {}
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.put(
                    url,
                    json=json,
                    headers=request_headers
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise
    
    async def delete(
        self,
        path: str,
        headers: Optional[Dict[str, Any]] = None,
        token: Optional[str] = None
    ) -> Dict[str, Any]:
        """Make a DELETE request to the service."""
        url = f"{self.base_url}{path}"
        
        request_headers = headers or {}
        if token:
            request_headers["Authorization"] = f"Bearer {token}"
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.delete(
                    url,
                    headers=request_headers
                )
                
                response.raise_for_status()
                return response.json()
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error: {e}")
            raise

# Service clients
user_service_client = ServiceClient(settings.USER_SERVICE_URL)
restaurant_service_client = ServiceClient(settings.RESTAURANT_SERVICE_URL)
driver_service_client = ServiceClient(settings.DRIVER_SERVICE_URL)
order_service_client = ServiceClient(settings.ORDER_SERVICE_URL)
analytics_service_client = ServiceClient(settings.ANALYTICS_SERVICE_URL)