import os
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    """Application settings."""
    
    # Application Settings
    SERVICE_NAME: str = Field("analytics-service", env="SERVICE_NAME")
    ENVIRONMENT: str = Field("development", env="ENVIRONMENT")
    DEBUG: bool = Field(True, env="DEBUG")
    
    # Kafka Settings
    KAFKA_BOOTSTRAP_SERVERS: str = Field("kafka:29092", env="KAFKA_BOOTSTRAP_SERVERS")
    
    # Apache Pinot Settings
    PINOT_CONTROLLER: str = Field("pinot-controller:9000", env="PINOT_CONTROLLER")
    PINOT_BROKER: str = Field("pinot-broker:8099", env="PINOT_BROKER")
    
    # JWT Settings
    JWT_SECRET: str = Field(..., env="JWT_SECRET")
    JWT_ALGORITHM: str = Field("HS256", env="JWT_ALGORITHM")
    
    # CORS Settings
    CORS_ORIGINS: list = ["*"]
    
    class Config:
        env_file = ".env"


settings = Settings()