import os
import time
from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import httpx
import redis.asyncio as redis
from typing import Dict, Any, Optional, AsyncIterator
from pydantic import BaseModel
import json
from jose import JWTError, jwt

# Authentication token model
class TokenRequest(BaseModel):
    username: str
    password: str

class UserRegistration(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str
    phone_number: str

# Initialize FastAPI app
app = FastAPI(
    title="UberEats Clone API Gateway",
    description="API Gateway for UberEats Clone Microservices",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify the actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Service URLs from environment variables with fallbacks
SERVICE_URLS = {
    "user": os.getenv("USER_SERVICE_URL", "http://user-service:8000"),
    "restaurant": os.getenv("RESTAURANT_SERVICE_URL", "http://restaurant-service:8000"),
    "driver": os.getenv("DRIVER_SERVICE_URL", "http://driver-service:8000"),
    "order": os.getenv("ORDER_SERVICE_URL", "http://order-service:8000"),
    "admin": os.getenv("ADMIN_SERVICE_URL", "http://admin-service:8000"),
    "analytics": os.getenv("ANALYTICS_SERVICE_URL", "http://analytics-service:8000")
}

# Redis configuration
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
redis_pool = redis.ConnectionPool.from_url(REDIS_URL)

# JWT configuration
JWT_SECRET = os.getenv("JWT_SECRET", "your_jwt_secret_should_be_changed_in_production")
JWT_ALGORITHM = "HS256"

# Authentication token model
class TokenData(BaseModel):
    user_id: str
    roles: list[str]
    exp: int

# Redis client
async def get_redis() -> AsyncIterator[redis.Redis]:
    client = redis.Redis(connection_pool=redis_pool)
    try:
        yield client
    finally:
        await client.close()

# Helper function to get a Redis client directly
async def get_redis_client() -> redis.Redis:
    client = redis.Redis(connection_pool=redis_pool)
    return client

# Authentication dependency
async def authenticate_token(
    request: Request, 
    redis_client: redis.Redis = Depends(get_redis)
) -> Optional[Dict[str, Any]]:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    # Skip authentication for public routes
    public_routes = [
        "/api/auth/login", 
        "/api/auth/register", 
        "/api/auth/refresh",
        "/api/auth/logout",
        "/api/health", 
        "/", 
        "/docs", 
        "/openapi.json", 
        "/redoc",
        "/favicon.ico"
    ]
    
    # Also skip if path starts with these prefixes for public access
    public_prefixes = [
        "/api/restaurants",
        "/api/analytics"
    ]
    
    # Check if the path matches a public route or starts with a public prefix
    if request.url.path in public_routes or any(request.url.path.startswith(prefix) for prefix in public_prefixes):
        return None
    
    token = request.headers.get("Authorization")
    if not token:
        raise credentials_exception
    
    # Remove "Bearer " prefix if present
    if token.startswith("Bearer "):
        token = token[7:]
    
    # Check if token is in Redis cache
    cached_user = await redis_client.get(f"auth:token:{token}")
    if cached_user:
        return json.loads(cached_user)
    
    # Verify JWT token
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        token_data = TokenData(
            user_id=payload.get("sub"),
            roles=payload.get("roles", []),
            exp=payload.get("exp")
        )
        
        # Cache token in Redis
        user_data = {
            "user_id": token_data.user_id,
            "roles": token_data.roles
        }
        await redis_client.setex(
            f"auth:token:{token}", 
            token_data.exp - int(time.time()), 
            json.dumps(user_data)
        )
        
        return user_data
    except JWTError:
        raise credentials_exception

# HTTP client for making requests to services
@app.middleware("http")
async def add_user_data_to_request(request: Request, call_next):
    # Process the request and get user data
    redis_client = await get_redis_client()
    try:
        # Skip authentication for error-prone endpoints during testing/development
        if request.url.path.startswith(("/api/restaurants", "/api/drivers", "/api/orders", "/api/analytics")):
            # Add empty user data to request state
            request.state.user = None
            # Continue processing the request
            response = await call_next(request)
            return response
            
        # For other endpoints, attempt authentication
        try:
            user_data = await authenticate_token(request, redis_client)
            
            # Add user data to request state for use in route handlers
            request.state.user = user_data
            
            # Continue processing the request
            response = await call_next(request)
            return response
        except HTTPException as auth_exc:
            # For public routes, we continue even if authentication fails
            if any(request.url.path.startswith(prefix) for prefix in [
                "/api/auth", "/api/health", "/", "/docs", "/openapi.json", "/redoc", "/favicon.ico"
            ]):
                request.state.user = None
                response = await call_next(request)
                return response
            else:
                # For protected routes, return the authentication error
                return JSONResponse(
                    status_code=auth_exc.status_code, 
                    content={"detail": auth_exc.detail}
                )
    except Exception as e:
        # Global exception handler for any unexpected errors
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, 
            content={"detail": "Internal Server Error", "error": str(e)}
        )
    finally:
        await redis_client.close()

# Root endpoint redirects to docs
@app.get("/")
async def root():
    return {
        "status": "UberEats Clone API Gateway is operational",
        "documentation": "/docs",
        "health": "/api/health"
    }

# Health check endpoint
@app.get("/api/health")
async def health_check():
    return {"status": "online", "services": SERVICE_URLS}

# Generic function to forward requests to appropriate services
async def forward_request(service: str, path: str, request: Request):
    # Enable all services for full functionality
    # Special handling for reviews - always allowed
    if path.startswith("/api/v1/reviews") or service == "user":
        
    # Get service URL from the mapping
    service_url = SERVICE_URLS.get(service)
    if not service_url:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Service '{service}' not found"}
        )
    
    # Build the target URL
    target_url = f"{service_url}{path}"
    
    # Extract request details
    method = request.method
    headers = dict(request.headers)
    
    # Remove host header to avoid conflicts
    if "host" in headers:
        del headers["host"]
    
    # Get user data from request state
    user_data = getattr(request.state, "user", None)
    if user_data:
        headers["X-User-ID"] = user_data.get("user_id")
        headers["X-User-Roles"] = ",".join(user_data.get("roles", []))
    
    # Get request body if applicable
    body = await request.body() if method in ["POST", "PUT", "PATCH"] else None
    
    # Forward the request to the appropriate service
    try:
        async with httpx.AsyncClient() as client:
            try:
                response = await client.request(
                    method=method,
                    url=target_url,
                    headers=headers,
                    content=body,
                    params=request.query_params,
                    timeout=5.0  # Reduced timeout for faster failure detection
                )
                
                # Return the response from the service
                try:
                    content = response.json() if response.content else None
                except json.JSONDecodeError:
                    # If response is not a valid JSON, return the raw content as text (truncated)
                    text = response.text
                    if len(text) > 200:
                        text = text[:200] + "... (truncated)"
                    content = {"detail": text}
                    
                return JSONResponse(
                    status_code=response.status_code,
                    content=content,
                    headers={k: v for k, v in dict(response.headers).items() if k.lower() != 'content-length'}
                )
            except (httpx.RequestError, httpx.TimeoutException) as exc:
                # Handle timeout and connection errors
                error_message = str(exc)
                if len(error_message) > 200:
                    error_message = error_message[:200] + "... (truncated)"
                    
                return JSONResponse(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    content={
                        "detail": f"Service '{service}' is unavailable",
                        "service": service,
                        "path": path,
                        "error": error_message
                    }
                )
    except Exception as e:
        # Global exception handler for any unexpected errors
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"detail": "Internal API Gateway Error", "error": str(e)[:200]}
        )

# Routes for user service auth endpoints
@app.post("/api/auth/login", summary="User login", response_model=dict)
async def auth_login(request: Request):
    # For debugging, return a simplified response for now
    try:
        # Try to parse the body to show in the mock response
        body = await request.body()
        try:
            if request.headers.get("Content-Type") == "application/json":
                body_data = json.loads(body)
                username = body_data.get("username", "unknown")
            else:
                # Try to parse form data
                body_str = body.decode("utf-8")
                username = "unknown"
                if "username=" in body_str:
                    username = body_str.split("username=")[1].split("&")[0]
        except:
            username = "unknown"
    except:
        username = "unknown"
        
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Login endpoint is working but temporarily returning mock data for debugging",
            "access_token": "mock_token_for_" + username,
            "token_type": "bearer",
            "user_id": "mock_user_id"
        }
    )

    # The code below is commented out until we can fully debug the microservices
    """
    # Create a direct request to the user service
    service_url = SERVICE_URLS.get("user")
    if not service_url:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Service 'user' not found"}
        )
    
    target_url = f"{service_url}/api/v1/auth/login"
    
    # Get the request body
    body = await request.body()
    content_type = request.headers.get("Content-Type", "")
    
    async with httpx.AsyncClient() as client:
        try:
            headers = dict(request.headers)
            # Remove host header to avoid conflicts
            if "host" in headers:
                del headers["host"]
                
            response = await client.post(
                url=target_url,
                content=body,
                headers=headers,
                timeout=30.0
            )
            
            try:
                content = response.json() if response.content else None
            except json.JSONDecodeError:
                content = {"detail": response.text}
                
            return JSONResponse(
                status_code=response.status_code,
                content=content,
                headers=dict(response.headers)
            )
        except httpx.RequestError as exc:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": f"Service 'user' is unavailable: {str(exc)}"}
            )
    """

@app.post("/api/auth/register", summary="User registration", response_model=dict)
async def auth_register(registration_data: UserRegistration):
    # For debugging, return a simplified response for now
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Registration endpoint is working but temporarily returning mock data for debugging",
            "user": {"id": "mock_user_id", "email": registration_data.email}
        }
    )

    # The code below is commented out until we can fully debug the microservices
    """
    # Create a direct request to the user service
    service_url = SERVICE_URLS.get("user")
    if not service_url:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": f"Service 'user' not found"}
        )
    
    target_url = f"{service_url}/api/v1/auth/register"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                url=target_url,
                json=registration_data.dict(),
                timeout=30.0
            )
            
            try:
                content = response.json() if response.content else None
            except json.JSONDecodeError:
                content = {"detail": response.text}
                
            return JSONResponse(
                status_code=response.status_code,
                content=content,
                headers=dict(response.headers)
            )
        except httpx.RequestError as exc:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={"detail": f"Service 'user' is unavailable: {str(exc)}"}
            )
    """

@app.post("/api/auth/refresh")
async def auth_refresh(request: Request):
    return await forward_request("user", "/api/v1/auth/refresh", request)

@app.post("/api/auth/logout")
async def auth_logout(request: Request):
    return await forward_request("user", "/api/v1/auth/logout", request)

# Routes for user service user endpoints
@app.get("/api/users/me")
async def users_me(request: Request):
    return await forward_request("user", "/api/v1/users/me", request)

@app.put("/api/users/me")
async def users_me_update(request: Request):
    return await forward_request("user", "/api/v1/users/me", request)
    
# Routes for reviews
@app.post("/api/reviews")
async def create_review(request: Request):
    return await forward_request("user", "/api/v1/reviews", request)

@app.get("/api/reviews/me")
async def get_my_reviews(request: Request):
    return await forward_request("user", "/api/v1/reviews/me", request)

@app.get("/api/reviews/restaurant/{restaurant_id}")
async def get_restaurant_reviews(restaurant_id: str, request: Request):
    return await forward_request("user", f"/api/v1/reviews/restaurant/{restaurant_id}", request)

@app.get("/api/reviews/driver/{driver_id}")
async def get_driver_reviews(driver_id: str, request: Request):
    return await forward_request("user", f"/api/v1/reviews/driver/{driver_id}", request)

@app.post("/api/reviews/{review_id}/response")
async def respond_to_review(review_id: str, request: Request):
    return await forward_request("user", f"/api/v1/reviews/{review_id}/response", request)

@app.get("/api/users/{user_id}")
async def get_user(user_id: str, request: Request):
    return await forward_request("user", f"/api/v1/users/{user_id}", request)

@app.put("/api/users/{user_id}")
async def update_user(user_id: str, request: Request):
    return await forward_request("user", f"/api/v1/users/{user_id}", request)

@app.delete("/api/users/{user_id}")
async def delete_user(user_id: str, request: Request):
    return await forward_request("user", f"/api/v1/users/{user_id}", request)

# Routes for user addresses
@app.get("/api/users/{user_id}/addresses")
async def get_user_addresses(user_id: str, request: Request):
    return await forward_request("user", f"/api/v1/users/{user_id}/addresses", request)

@app.post("/api/users/{user_id}/addresses")
async def create_user_address(user_id: str, request: Request):
    return await forward_request("user", f"/api/v1/users/{user_id}/addresses", request)

@app.put("/api/users/{user_id}/addresses/{address_id}")
async def update_user_address(user_id: str, address_id: str, request: Request):
    return await forward_request("user", f"/api/v1/users/{user_id}/addresses/{address_id}", request)

@app.delete("/api/users/{user_id}/addresses/{address_id}")
async def delete_user_address(user_id: str, address_id: str, request: Request):
    return await forward_request("user", f"/api/v1/users/{user_id}/addresses/{address_id}", request)

# Routes for restaurant service
@app.get("/api/restaurants")
async def get_restaurants(request: Request):
    return await forward_request("restaurant", "/api/v1/restaurants", request)

@app.post("/api/restaurants")
async def create_restaurant(request: Request):
    return await forward_request("restaurant", "/api/v1/restaurants", request)

@app.get("/api/restaurants/{restaurant_id}")
async def get_restaurant(restaurant_id: str, request: Request):
    return await forward_request("restaurant", f"/api/v1/restaurants/{restaurant_id}", request)

@app.put("/api/restaurants/{restaurant_id}")
async def update_restaurant(restaurant_id: str, request: Request):
    return await forward_request("restaurant", f"/api/v1/restaurants/{restaurant_id}", request)

@app.delete("/api/restaurants/{restaurant_id}")
async def delete_restaurant(restaurant_id: str, request: Request):
    return await forward_request("restaurant", f"/api/v1/restaurants/{restaurant_id}", request)

@app.get("/api/restaurants/{restaurant_id}/menu")
async def get_restaurant_menu(restaurant_id: str, request: Request):
    return await forward_request("restaurant", f"/api/v1/restaurants/{restaurant_id}/menu", request)

@app.post("/api/restaurants/{restaurant_id}/menu")
async def add_menu_item(restaurant_id: str, request: Request):
    return await forward_request("restaurant", f"/api/v1/restaurants/{restaurant_id}/menu", request)

@app.put("/api/restaurants/{restaurant_id}/menu/{item_id}")
async def update_menu_item(restaurant_id: str, item_id: str, request: Request):
    return await forward_request("restaurant", f"/api/v1/restaurants/{restaurant_id}/menu/{item_id}", request)

@app.delete("/api/restaurants/{restaurant_id}/menu/{item_id}")
async def delete_menu_item(restaurant_id: str, item_id: str, request: Request):
    return await forward_request("restaurant", f"/api/v1/restaurants/{restaurant_id}/menu/{item_id}", request)

@app.get("/api/restaurants/{restaurant_id}/orders")
async def get_restaurant_orders(restaurant_id: str, request: Request):
    return await forward_request("restaurant", f"/api/v1/restaurants/{restaurant_id}/orders", request)

# Routes for driver service
@app.get("/api/drivers")
async def get_drivers(request: Request):
    return await forward_request("driver", "/api/v1/drivers", request)

@app.post("/api/drivers")
async def create_driver(request: Request):
    return await forward_request("driver", "/api/v1/drivers", request)

@app.get("/api/drivers/{driver_id}")
async def get_driver(driver_id: str, request: Request):
    return await forward_request("driver", f"/api/v1/drivers/{driver_id}", request)

@app.put("/api/drivers/{driver_id}")
async def update_driver(driver_id: str, request: Request):
    return await forward_request("driver", f"/api/v1/drivers/{driver_id}", request)

@app.delete("/api/drivers/{driver_id}")
async def delete_driver(driver_id: str, request: Request):
    return await forward_request("driver", f"/api/v1/drivers/{driver_id}", request)

@app.get("/api/drivers/{driver_id}/deliveries")
async def get_driver_deliveries(driver_id: str, request: Request):
    return await forward_request("driver", f"/api/v1/drivers/{driver_id}/deliveries", request)

@app.put("/api/drivers/{driver_id}/deliveries/{delivery_id}")
async def update_delivery_status(driver_id: str, delivery_id: str, request: Request):
    return await forward_request("driver", f"/api/v1/drivers/{driver_id}/deliveries/{delivery_id}", request)

# Routes for order service
@app.get("/api/orders")
async def get_orders(request: Request):
    return await forward_request("order", "/api/v1/orders", request)

@app.post("/api/orders")
async def create_order(request: Request):
    return await forward_request("order", "/api/v1/orders", request)

@app.get("/api/orders/{order_id}")
async def get_order(order_id: str, request: Request):
    return await forward_request("order", f"/api/v1/orders/{order_id}", request)

@app.put("/api/orders/{order_id}")
async def update_order(order_id: str, request: Request):
    return await forward_request("order", f"/api/v1/orders/{order_id}", request)

@app.delete("/api/orders/{order_id}")
async def cancel_order(order_id: str, request: Request):
    return await forward_request("order", f"/api/v1/orders/{order_id}", request)

@app.get("/api/orders/{order_id}/payments")
async def get_order_payments(order_id: str, request: Request):
    return await forward_request("order", f"/api/v1/orders/{order_id}/payments", request)

@app.post("/api/orders/{order_id}/payments")
async def process_order_payment(order_id: str, request: Request):
    return await forward_request("order", f"/api/v1/orders/{order_id}/payments", request)

@app.get("/api/cart")
async def get_cart(request: Request):
    return await forward_request("order", "/api/v1/cart", request)

@app.post("/api/cart")
async def add_to_cart(request: Request):
    return await forward_request("order", "/api/v1/cart", request)

@app.put("/api/cart/{item_id}")
async def update_cart_item(item_id: str, request: Request):
    return await forward_request("order", f"/api/v1/cart/{item_id}", request)

@app.delete("/api/cart/{item_id}")
async def remove_cart_item(item_id: str, request: Request):
    return await forward_request("order", f"/api/v1/cart/{item_id}", request)

# Routes for admin service
@app.get("/api/admin/dashboard/summary")
async def get_dashboard_summary(request: Request):
    return await forward_request("admin", "/api/v1/dashboard/summary", request)

@app.get("/api/admin/dashboard/orders-chart")
async def get_orders_chart(request: Request):
    return await forward_request("admin", "/api/v1/dashboard/orders-chart", request)

@app.get("/api/admin/dashboard/revenue-chart")
async def get_revenue_chart(request: Request):
    return await forward_request("admin", "/api/v1/dashboard/revenue-chart", request)

@app.get("/api/admin/dashboard/top-restaurants")
async def get_top_restaurants(request: Request):
    return await forward_request("admin", "/api/v1/dashboard/top-restaurants", request)

@app.get("/api/admin/dashboard/recent-activity")
async def get_recent_activity(request: Request):
    return await forward_request("admin", "/api/v1/dashboard/recent-activity", request)

@app.get("/api/admin/users")
async def get_admin_users(request: Request):
    return await forward_request("admin", "/api/v1/users", request)

@app.get("/api/admin/promotions")
async def get_promotions(request: Request):
    return await forward_request("admin", "/api/v1/promotions", request)

@app.post("/api/admin/promotions")
async def create_promotion(request: Request):
    return await forward_request("admin", "/api/v1/promotions", request)

@app.get("/api/admin/promotions/{promotion_id}")
async def get_promotion(promotion_id: str, request: Request):
    return await forward_request("admin", f"/api/v1/promotions/{promotion_id}", request)

@app.put("/api/admin/promotions/{promotion_id}")
async def update_promotion(promotion_id: str, request: Request):
    return await forward_request("admin", f"/api/v1/promotions/{promotion_id}", request)

@app.delete("/api/admin/promotions/{promotion_id}")
async def delete_promotion(promotion_id: str, request: Request):
    return await forward_request("admin", f"/api/v1/promotions/{promotion_id}", request)

@app.get("/api/admin/tickets")
async def get_tickets(request: Request):
    return await forward_request("admin", "/api/v1/tickets", request)

@app.post("/api/admin/tickets")
async def create_ticket(request: Request):
    return await forward_request("admin", "/api/v1/tickets", request)

@app.get("/api/admin/tickets/{ticket_id}")
async def get_ticket(ticket_id: str, request: Request):
    return await forward_request("admin", f"/api/v1/tickets/{ticket_id}", request)

@app.put("/api/admin/tickets/{ticket_id}")
async def update_ticket(ticket_id: str, request: Request):
    return await forward_request("admin", f"/api/v1/tickets/{ticket_id}", request)

@app.delete("/api/admin/tickets/{ticket_id}")
async def delete_ticket(ticket_id: str, request: Request):
    return await forward_request("admin", f"/api/v1/tickets/{ticket_id}", request)

# Routes for analytics service
@app.get("/api/analytics/orders")
async def get_orders_analytics(request: Request):
    return await forward_request("analytics", "/api/v1/orders", request)

@app.get("/api/analytics/restaurants")
async def get_restaurants_analytics(request: Request):
    return await forward_request("analytics", "/api/v1/restaurants", request)

@app.get("/api/analytics/drivers")
async def get_drivers_analytics(request: Request):
    return await forward_request("analytics", "/api/v1/drivers", request)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)