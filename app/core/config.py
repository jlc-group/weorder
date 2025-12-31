from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "WeOrder"
    APP_PORT: int = 9202
    DEBUG: bool = True
    SECRET_KEY: str = "weorder-secret-key-change-in-production"
    
    # Database
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "postgres"
    POSTGRES_PASSWORD: str = "postgres"
    POSTGRES_DB: str = "weorder"
    POSTGRES_PORT: int = 5432
    
    # Paths
    DATA_PATH: str = "D:/IISSERVER/data/weorder"
    LOGS_PATH: str = "D:/IISSERVER/logs/weorder"
    
    @property
    def DATABASE_URL(self) -> str:
        return f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
    
    class Config:
        env_file = "D:/IISSERVER/run/weorder/.env"
        extra = "ignore"

@lru_cache()
def get_settings() -> Settings:
    return Settings()

settings = get_settings()
