from pydantic import BaseModel
from typing import Dict, List, Any, Optional
from datetime import datetime


class DriverPerformanceMetric(BaseModel):
    """Performance metrics for a single driver."""
    driver_id: str
    delivery_count: int
    avg_delivery_time: float
    avg_rating: float
    total_tips: float


class DriverPerformanceResponse(BaseModel):
    """Response model for driver performance metrics."""
    metrics: List[DriverPerformanceMetric]
    total_drivers: int
    time_period: Dict[str, str]


class DeliveryTimeDistribution(BaseModel):
    """Distribution of delivery times by time range."""
    time_ranges: Dict[str, int]
    total_deliveries: int
    time_period: Dict[str, str]


class DailyStats(BaseModel):
    """Daily statistics for a driver."""
    delivery_date: str
    delivery_count: int
    avg_delivery_time: float
    total_tips: float


class DriverDailyStatsResponse(BaseModel):
    """Response model for driver daily statistics."""
    driver_id: str
    daily_stats: List[DailyStats]
    time_period: Dict[str, str]