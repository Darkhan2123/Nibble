import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings."""
    
    # Application Settings
    SERVICE_NAME: str = Field("notification-service", env="SERVICE_NAME")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(True, env="DEBUG")
    
    # Redis Settings
    REDIS_URL: str = Field("redis://redis:6379/0", env="REDIS_URL")
    
    # Kafka Settings
    KAFKA_BOOTSTRAP_SERVERS: str = Field("kafka:29092", env="KAFKA_BOOTSTRAP_SERVERS")
    
    # JWT Settings
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    
    # Email Settings (for sending notifications)
    SMTP_SERVER: str = Field("smtp.example.com", env="SMTP_SERVER")
    SMTP_PORT: int = Field(587, env="SMTP_PORT")
    SMTP_USERNAME: str = Field("notifications@example.com", env="SMTP_USERNAME")
    SMTP_PASSWORD: str = Field("password", env="SMTP_PASSWORD")
    EMAIL_FROM: str = Field("UberEats Clone <notifications@example.com>", env="EMAIL_FROM")
    
    # SMS Settings (mock implementation)
    SMS_ENABLED: bool = Field(False, env="SMS_ENABLED")
    
    # Push Notification Settings (mock implementation)
    PUSH_ENABLED: bool = Field(False, env="PUSH_ENABLED")
    
    # CORS Settings
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"


settings = Settings()