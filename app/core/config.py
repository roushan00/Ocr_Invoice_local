from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    # App
    MODEL_NAME: str
    APP_NAME: str = 'Georgia'
    LOCAL_STORAGE_BASE_PATH: str
    DEBUG: bool = False

    # Database
    DB_HOST: str
    DB_PORT: str
    DB_NAME: str
    DB_USER: str
    DB_PASSWORD: str
    DB_SCHEMA: str = 'public'

    # Status
    STATUS_QUEUE: int
    STATUS_PROCESSING: int
    STATUS_COMPLETED: int
    STATUS_ERROR: int

    # 🔴 REDIS CONFIG (ADD THIS)
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_DB: int
    REDIS_PASSWORD: str | None = None

    class Config:
        env_file = '.env'


settings = Settings()
