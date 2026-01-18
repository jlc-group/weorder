from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "WeOrder"
    APP_PORT: int = 9202
    DEBUG: bool = False  # Set to True only for development debugging
    SECRET_KEY: str = "weorder-secret-key-change-in-production"
    TIMEZONE: str = "Asia/Bangkok"
    
    # Database - Loaded from environment variables / .env file
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = ""  # Set via POSTGRES_PASSWORD env var or .env
    POSTGRES_DB: str = "weorder"
    POSTGRES_PORT: int = 5432
    
    # Paths
    DATA_PATH: str = os.getenv("DATA_PATH", "./data")
    LOGS_PATH: str = os.getenv("LOGS_PATH", "./logs")
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    class Config:
        env_file = ".env"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
