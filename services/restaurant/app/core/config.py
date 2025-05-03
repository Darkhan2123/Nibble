import os
from pydantic_settings import BaseSettings
from typing import List, Optional

class Settings(BaseSettings):
    # App configuration
    APP_NAME: str = "UberEats Clone Restaurant Service"
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
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # CORS configuration
    CORS_ORIGINS: List[str] = ["*"]
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Default pagination
    DEFAULT_LIMIT: int = 100
    
    # File upload
    MAX_UPLOAD_SIZE: int = 10 * 1024 * 1024  # 10MB
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]
    
    # Default restaurant parameters
    DEFAULT_COMMISSION_RATE: float = 15.0
    DEFAULT_DELIVERY_RADIUS: int = 5000  # meters
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

# Initialize settings
settings = Settings()