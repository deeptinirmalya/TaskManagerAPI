import os
from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):

    USER_NAME: str = os.getenv("USER_NAME")
    PASSWORD: str = os.getenv("PASSWORD")

    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    ACCESS_TOKEN_EXPIRE_MINUTES_SHORT: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES_SHORT", 15))
    ACCESS_TOKEN_EXPIRE_MLSECOND_SHORT: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MLSECOND_SHORT", 900000))

    ACCESS_TOKEN_EXPIRE_MINUTES_LONG: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES_LONG", 10080))
    ACCESS_TOKEN_EXPIRE_MLSECOND_LONG: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MLSECOND_LONG", 604800000))

    SECRET_KEY: str = os.getenv("SECRET_KEY")

    PUSHBULLET_AUTH_KEY: str = os.getenv("PUSHBULLET_AUTH_KEY")

    API_ACCESS_KEY: str = os.getenv("API_ACCESS_KEY")

    CELERY_WORKER_BROKER_URL: str = os.getenv("CELERY_WORKER_BROKER_URL")

    PYTHON_ENV: str = os.getenv("PYTHON_ENV", "production")
    ALLOWED_ORIGINS: str = os.getenv("ALLOWED_ORIGINS", "https://task-manager-client-plum.vercel.app")














    @property
    def BACKEND_CORS_ORIGINS(self) -> list[str]:
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    class Config:
        case_sensitive = True

settings = Settings()
