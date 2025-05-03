import os
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # App configuration
    APP_NAME: str = "UberEats Clone Driver Service"
    API_V1_STR: str = "/v1"
    
    # Database configuration
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://ubereats:ubereats_password@postgres:5432/ubereats")
    DB_MIN_POOL_SIZE: int = 10
    DB_MAX_POOL_SIZE: int = 100
    DB_MAX_INACTIVE_CONN_LIFETIME: int = 300  # seconds
    
    # Redis configuration
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    
    # Kafka configuration
    KAFKA_BOOTSTRAP_SERVERS: str = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "kafka:29092")
    
    # JWT configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "your_jwt_secret_should_be_changed_in_production")
    JWT_ALGORITHM: str = "HS256"
    
    # Yandex Maps API configuration
    YANDEX_MAP_API_KEY: str = os.getenv("YANDEX_MAP_API_KEY", "4187db56-ead5-458f-85c4-f6483ae62c1a")
    YANDEX_MAP_API_URL: str = "https://geocode-maps.yandex.ru/1.x"
    YANDEX_ROUTING_API_URL: str = "https://api.routing.yandex.net/v2/route"
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # CORS configuration
    CORS_ORIGINS: List[str] = ["*"]
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Default pagination
    DEFAULT_LIMIT: int = 100
    
    # Driver specific settings
    LOCATION_UPDATE_INTERVAL: int = 30  # seconds
    LOCATION_EXPIRY_TIME: int = 300  # seconds
    DRIVER_SEARCH_RADIUS: int = 5000  # meters
    MAX_ACTIVE_DELIVERIES: int = 2  # Maximum deliveries a driver can have active at once
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Initialize settings
settings = Settings()