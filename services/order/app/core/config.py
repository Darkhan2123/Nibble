import os
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # App configuration
    APP_NAME: str = "UberEats Clone Order Service"
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
    
    # Payment configuration
    STRIPE_API_KEY: str = os.getenv("STRIPE_API_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    PAYMENT_EXPIRATION_MINUTES: int = 30
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # CORS configuration
    CORS_ORIGINS: List[str] = ["*"]
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Default pagination
    DEFAULT_LIMIT: int = 100
    
    # Order specific settings
    ORDER_NUMBER_PREFIX: str = "OD"
    DEFAULT_TAX_RATE: float = 0.08  # 8% tax
    DRIVER_ASSIGNMENT_RADIUS: int = 5000  # meters
    DELIVERY_RETRY_COUNT: int = 3
    DELIVERY_TIMEOUT_SECONDS: int = 300  # 5 minutes
    
    # Service URLs for internal communication
    DRIVER_SERVICE_URL: str = os.getenv("DRIVER_SERVICE_URL", "http://driver-service:8000/api")
    RESTAURANT_SERVICE_URL: str = os.getenv("RESTAURANT_SERVICE_URL", "http://restaurant-service:8000/api")
    USER_SERVICE_URL: str = os.getenv("USER_SERVICE_URL", "http://user-service:8000/api")
    
    # Internal API key for service-to-service communication
    INTERNAL_API_KEY: str = os.getenv("INTERNAL_API_KEY", "internal-api-key-for-development")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Initialize settings
settings = Settings()