
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db:5432/postgres")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://redis:6379/0")
    API_KEYS: str = os.getenv("API_KEYS", "test_key")

settings = Settings()
