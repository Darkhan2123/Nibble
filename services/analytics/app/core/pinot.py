import logging
import httpx
import json
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)

class PinotClient:
    """Client for interacting with Apache Pinot."""
    
    def __init__(self):
        """Initialize the Pinot client."""
        self.controller_url = f"http://{settings.PINOT_CONTROLLER}"
        self.broker_url = f"http://{settings.PINOT_BROKER}"
    
    async def check_health(self) -> bool:
        """Check if Pinot controller is healthy."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.controller_url}/health")
                return response.status_code == 200
        except Exception as e:
            logger.error(f"Failed to check Pinot health: {e}")
            return False
    
    async def execute_query(self, query: str) -> Dict[str, Any]:
        """Execute a SQL query on Pinot."""
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.broker_url}/query/sql",
                    json={"sql": query}
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Pinot query failed with status {response.status_code}: {response.text}")
                    return {"error": f"Query failed with status {response.status_code}"}
                    
        except Exception as e:
            logger.error(f"Failed to execute Pinot query: {e}")
            return {"error": str(e)}
    
    async def get_tables(self) -> List[str]:
        """Get list of tables in Pinot."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.controller_url}/tables")
                
                if response.status_code == 200:
                    return response.json()["tables"]
                else:
                    logger.error(f"Failed to get Pinot tables: {response.status_code}")
                    return []
                    
        except Exception as e:
            logger.error(f"Failed to get Pinot tables: {e}")
            return []
    
    async def get_schema(self, schema_name: str) -> Optional[Dict[str, Any]]:
        """Get a schema from Pinot."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{self.controller_url}/schemas/{schema_name}")
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.error(f"Failed to get Pinot schema {schema_name}: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Failed to get Pinot schema {schema_name}: {e}")
            return None
    
    # Order Analytics Queries
    
    async def get_order_count(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        restaurant_id: Optional[str] = None,
        status: Optional[str] = None
    ) -> int:
        """Get the count of orders in a given time period."""
        # Default to last 7 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Convert to milliseconds timestamp
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # Build the query
        query = f"SELECT COUNT(*) as order_count FROM orders WHERE created_at BETWEEN {start_ts} AND {end_ts}"
        
        # Add filters
        if restaurant_id:
            query += f" AND restaurant_id = '{restaurant_id}'"
        if status:
            query += f" AND status = '{status}'"
        
        # Execute query
        result = await self.execute_query(query)
        
        # Parse result
        if "resultTable" in result and "rows" in result["resultTable"] and len(result["resultTable"]["rows"]) > 0:
            return result["resultTable"]["rows"][0][0]
        
        return 0
    
    async def get_order_revenue(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        restaurant_id: Optional[str] = None
    ) -> float:
        """Get the total revenue from orders in a given time period."""
        # Default to last 7 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Convert to milliseconds timestamp
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # Build the query
        query = f"SELECT SUM(total_amount) as total_revenue FROM orders WHERE created_at BETWEEN {start_ts} AND {end_ts} AND status != 'cancelled'"
        
        # Add filters
        if restaurant_id:
            query += f" AND restaurant_id = '{restaurant_id}'"
        
        # Execute query
        result = await self.execute_query(query)
        
        # Parse result
        if "resultTable" in result and "rows" in result["resultTable"] and len(result["resultTable"]["rows"]) > 0:
            return float(result["resultTable"]["rows"][0][0] or 0)
        
        return 0.0
    
    async def get_order_status_breakdown(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        restaurant_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Get the breakdown of orders by status in a given time period."""
        # Default to last 7 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Convert to milliseconds timestamp
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # Build the query
        query = f"SELECT status, COUNT(*) as count FROM orders WHERE created_at BETWEEN {start_ts} AND {end_ts}"
        
        # Add filters
        if restaurant_id:
            query += f" AND restaurant_id = '{restaurant_id}'"
        
        query += " GROUP BY status"
        
        # Execute query
        result = await self.execute_query(query)
        
        # Parse result
        status_breakdown = {}
        if "resultTable" in result and "rows" in result["resultTable"]:
            for row in result["resultTable"]["rows"]:
                status_breakdown[row[0]] = row[1]
        
        return status_breakdown
    
    async def get_orders_by_hour(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        restaurant_id: Optional[str] = None
    ) -> Dict[int, int]:
        """Get the number of orders by hour of day in a given time period."""
        # Default to last 7 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Convert to milliseconds timestamp
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # Build the query - extract hour from created_at
        query = f"SELECT HOUR(from_unixtime_millis(created_at)) as hour, COUNT(*) as count FROM orders WHERE created_at BETWEEN {start_ts} AND {end_ts}"
        
        # Add filters
        if restaurant_id:
            query += f" AND restaurant_id = '{restaurant_id}'"
        
        query += " GROUP BY HOUR(from_unixtime_millis(created_at)) ORDER BY hour"
        
        # Execute query
        result = await self.execute_query(query)
        
        # Parse result
        hours_breakdown = {}
        if "resultTable" in result and "rows" in result["resultTable"]:
            for row in result["resultTable"]["rows"]:
                hours_breakdown[row[0]] = row[1]
        
        return hours_breakdown
    
    async def get_top_restaurants(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get the top restaurants by order count in a given time period."""
        # Default to last 7 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Convert to milliseconds timestamp
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # Build the query
        query = f"""
        SELECT 
            restaurant_id, 
            COUNT(*) as order_count, 
            SUM(total_amount) as total_revenue 
        FROM orders 
        WHERE created_at BETWEEN {start_ts} AND {end_ts} AND status != 'cancelled'
        GROUP BY restaurant_id 
        ORDER BY order_count DESC 
        LIMIT {limit}
        """
        
        # Execute query
        result = await self.execute_query(query)
        
        # Parse result
        top_restaurants = []
        if "resultTable" in result and "rows" in result["resultTable"]:
            columns = result["resultTable"]["columns"]
            for row in result["resultTable"]["rows"]:
                restaurant = {}
                for i, col in enumerate(columns):
                    restaurant[col] = row[i]
                top_restaurants.append(restaurant)
        
        return top_restaurants
    
    async def get_average_order_value(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        restaurant_id: Optional[str] = None
    ) -> float:
        """Get the average order value in a given time period."""
        # Default to last 7 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Convert to milliseconds timestamp
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # Build the query
        query = f"SELECT AVG(total_amount) as avg_order_value FROM orders WHERE created_at BETWEEN {start_ts} AND {end_ts} AND status != 'cancelled'"
        
        # Add filters
        if restaurant_id:
            query += f" AND restaurant_id = '{restaurant_id}'"
        
        # Execute query
        result = await self.execute_query(query)
        
        # Parse result
        if "resultTable" in result and "rows" in result["resultTable"] and len(result["resultTable"]["rows"]) > 0:
            return float(result["resultTable"]["rows"][0][0] or 0)
        
        return 0.0
    
    async def get_average_delivery_time(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        restaurant_id: Optional[str] = None
    ) -> float:
        """Get the average delivery time in minutes in a given time period."""
        # Default to last 7 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Convert to milliseconds timestamp
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # Build the query
        query = f"SELECT AVG(total_time_minutes) as avg_delivery_time FROM orders WHERE created_at BETWEEN {start_ts} AND {end_ts} AND status = 'delivered'"
        
        # Add filters
        if restaurant_id:
            query += f" AND restaurant_id = '{restaurant_id}'"
        
        # Execute query
        result = await self.execute_query(query)
        
        # Parse result
        if "resultTable" in result and "rows" in result["resultTable"] and len(result["resultTable"]["rows"]) > 0:
            return float(result["resultTable"]["rows"][0][0] or 0)
        
        return 0.0
    
    # Driver Analytics Queries
    
    async def get_driver_performance_metrics(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        driver_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get performance metrics for drivers in a given time period."""
        # Default to last 7 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Convert to milliseconds timestamp
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # Build the query
        query = f"""
        SELECT 
            driver_id, 
            COUNT(*) as delivery_count, 
            AVG(delivery_time_minutes) as avg_delivery_time, 
            AVG(delivery_rating) as avg_rating,
            SUM(tip) as total_tips
        FROM orders 
        WHERE created_at BETWEEN {start_ts} AND {end_ts} 
        AND status = 'delivered' 
        """
        
        # Add filters
        if driver_id:
            query += f" AND driver_id = '{driver_id}'"
        
        query += """
        GROUP BY driver_id 
        ORDER BY delivery_count DESC 
        """
        
        if not driver_id:
            query += f" LIMIT {limit}"
        
        # Execute query
        result = await self.execute_query(query)
        
        # Parse result
        driver_metrics = []
        if "resultTable" in result and "rows" in result["resultTable"]:
            columns = result["resultTable"]["columns"]
            for row in result["resultTable"]["rows"]:
                driver_data = {}
                for i, col in enumerate(columns):
                    # Convert numeric values to appropriate types
                    if col in ["avg_delivery_time", "avg_rating", "total_tips"]:
                        driver_data[col] = float(row[i] or 0)
                    elif col == "delivery_count":
                        driver_data[col] = int(row[i])
                    else:
                        driver_data[col] = row[i]
                driver_metrics.append(driver_data)
        
        return driver_metrics
    
    async def get_driver_delivery_times_distribution(
        self, 
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None,
        driver_id: Optional[str] = None
    ) -> Dict[str, int]:
        """Get the distribution of delivery times for drivers."""
        # Default to last 7 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Convert to milliseconds timestamp
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # Define time ranges in minutes
        time_ranges = [
            "CASE WHEN delivery_time_minutes < 15 THEN 'Under 15 min' " +
            "WHEN delivery_time_minutes < 30 THEN '15-30 min' " +
            "WHEN delivery_time_minutes < 45 THEN '30-45 min' " +
            "WHEN delivery_time_minutes < 60 THEN '45-60 min' " +
            "ELSE 'Over 60 min' END as time_range"
        ]
        
        # Build the query
        query = f"""
        SELECT 
            {time_ranges[0]}, 
            COUNT(*) as count 
        FROM orders 
        WHERE created_at BETWEEN {start_ts} AND {end_ts} 
        AND status = 'delivered' 
        """
        
        # Add filters
        if driver_id:
            query += f" AND driver_id = '{driver_id}'"
        
        query += " GROUP BY time_range ORDER BY time_range"
        
        # Execute query
        result = await self.execute_query(query)
        
        # Parse result
        time_distribution = {}
        if "resultTable" in result and "rows" in result["resultTable"]:
            for row in result["resultTable"]["rows"]:
                time_distribution[row[0]] = row[1]
        
        # Ensure all time ranges are in the result
        all_ranges = ["Under 15 min", "15-30 min", "30-45 min", "45-60 min", "Over 60 min"]
        for time_range in all_ranges:
            if time_range not in time_distribution:
                time_distribution[time_range] = 0
                
        return time_distribution
    
    async def get_driver_daily_stats(
        self, 
        driver_id: str,
        start_date: Optional[datetime] = None, 
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Get daily stats for a specific driver."""
        # Default to last 7 days if no dates provided
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=7)
        if not end_date:
            end_date = datetime.utcnow()
        
        # Convert to milliseconds timestamp
        start_ts = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # Build the query to get daily stats
        query = f"""
        SELECT 
            DATETRUNC('day', from_unixtime_millis(created_at)) as delivery_date,
            COUNT(*) as delivery_count, 
            AVG(delivery_time_minutes) as avg_delivery_time, 
            SUM(tip) as total_tips
        FROM orders 
        WHERE created_at BETWEEN {start_ts} AND {end_ts} 
        AND status = 'delivered' 
        AND driver_id = '{driver_id}'
        GROUP BY DATETRUNC('day', from_unixtime_millis(created_at))
        ORDER BY delivery_date
        """
        
        # Execute query
        result = await self.execute_query(query)
        
        # Parse result
        daily_stats = []
        if "resultTable" in result and "rows" in result["resultTable"]:
            columns = result["resultTable"]["columns"]
            for row in result["resultTable"]["rows"]:
                day_data = {}
                for i, col in enumerate(columns):
                    if col == "delivery_date":
                        # Convert to date string
                        day_data[col] = row[i].split(" ")[0]  # Extract just the date part
                    elif col in ["avg_delivery_time", "total_tips"]:
                        day_data[col] = float(row[i] or 0)
                    else:
                        day_data[col] = row[i]
                daily_stats.append(day_data)
        
        return daily_stats

# Global client instance
pinot_client = PinotClient()

async def get_pinot_client() -> PinotClient:
    """Get the Pinot client."""
    return pinot_client