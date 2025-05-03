from fastapi import APIRouter, Request, Depends, HTTPException
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os
from pathlib import Path

from app.core.auth import get_current_admin

# Setup templates directory
templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=templates_dir)

# Create router
dashboard_router = APIRouter()

@dashboard_router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request, current_user=Depends(get_current_admin)):
    """
    Render the main dashboard page.
    
    This page shows an overview of all analytics metrics.
    """
    return templates.TemplateResponse(
        "dashboard.html", 
        {"request": request, "active_page": "dashboard"}
    )

@dashboard_router.get("/drivers", response_class=HTMLResponse)
async def drivers_dashboard(request: Request, current_user=Depends(get_current_admin)):
    """
    Render the drivers analytics dashboard.
    
    This page shows performance metrics for drivers.
    """
    return templates.TemplateResponse(
        "drivers.html", 
        {"request": request, "active_page": "drivers"}
    )

@dashboard_router.get("/delivery-times", response_class=HTMLResponse)
async def delivery_times_dashboard(request: Request, current_user=Depends(get_current_admin)):
    """
    Render the delivery times analytics dashboard.
    
    This page shows detailed delivery time metrics.
    """
    return templates.TemplateResponse(
        "delivery_times.html", 
        {"request": request, "active_page": "delivery_times"}
    )

@dashboard_router.get("/restaurants", response_class=HTMLResponse)
async def restaurants_dashboard(request: Request, current_user=Depends(get_current_admin)):
    """
    Render the restaurants analytics dashboard.
    
    This page shows performance metrics for restaurants.
    """
    return templates.TemplateResponse(
        "restaurants.html", 
        {"request": request, "active_page": "restaurants"}
    )

@dashboard_router.get("/orders", response_class=HTMLResponse)
async def orders_dashboard(request: Request, current_user=Depends(get_current_admin)):
    """
    Render the orders analytics dashboard.
    
    This page shows metrics related to orders.
    """
    return templates.TemplateResponse(
        "orders.html", 
        {"request": request, "active_page": "orders"}
    )

@dashboard_router.get("/revenue", response_class=HTMLResponse)
async def revenue_dashboard(request: Request, current_user=Depends(get_current_admin)):
    """
    Render the revenue analytics dashboard.
    
    This page shows metrics related to order revenue.
    """
    return templates.TemplateResponse(
        "revenue.html", 
        {"request": request, "active_page": "revenue"}
    )