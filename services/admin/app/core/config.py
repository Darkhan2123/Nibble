import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings."""
    
    # Application Settings
    SERVICE_NAME: str = Field("admin-service", env="SERVICE_NAME")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(True, env="DEBUG")
    
    # Database Settings
    DATABASE_URL: str = Field(..., env="DATABASE_URL")
    
    # Redis Settings
    REDIS_URL: str = Field("redis://redis:6379/0", env="REDIS_URL")
    
    # Kafka Settings
    KAFKA_BOOTSTRAP_SERVERS: str = Field("kafka:29092", env="KAFKA_BOOTSTRAP_SERVERS")
    
    # JWT Settings
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(30, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Services URLs
    USER_SERVICE_URL: str = Field("http://user-service:8000", env="USER_SERVICE_URL")
    RESTAURANT_SERVICE_URL: str = Field("http://restaurant-service:8000", env="RESTAURANT_SERVICE_URL")
    DRIVER_SERVICE_URL: str = Field("http://driver-service:8000", env="DRIVER_SERVICE_URL")
    ORDER_SERVICE_URL: str = Field("http://order-service:8000", env="ORDER_SERVICE_URL")
    ANALYTICS_SERVICE_URL: str = Field("http://analytics-service:8000", env="ANALYTICS_SERVICE_URL")
    
    # CORS Settings
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"

settings = Settings()