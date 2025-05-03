import os
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache

class Settings(BaseSettings):
    # App configuration
    APP_NAME: str = "UberEats Clone User Service"
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
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days
    
    # Environment
    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    
    # CORS configuration
    CORS_ORIGINS: List[str] = ["*"]
    
    # Logging configuration
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    
    # Yandex Maps API configuration
    YANDEX_MAP_API_KEY: str = os.getenv("YANDEX_MAP_API_KEY", "21e19bef-11d6-44c7-bfb3-4ac445da79e7")
    YANDEX_MAP_API_URL: str = "https://geocode-maps.yandex.ru/1.x"
    YANDEX_ROUTING_API_URL: str = "https://api.routing.yandex.net/v2/route"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True

@lru_cache()
def get_settings():
    return Settings()

settings = get_settings()