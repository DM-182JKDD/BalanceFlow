from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    APP_NAME: str = "BalanceFlow API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # Base de datos (SQLite por ahora; cambiar a PostgreSQL en producción)
    DATABASE_URL: str = "sqlite:///./balanceflow.db"

    # Firma los tokens de sesión. Definirlo por entorno antes de exponer la API.
    SECRET_KEY: str = "definir-por-entorno"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    ADMIN_EMAIL: str = "admin@balanceflow.local"
    ADMIN_PASSWORD: str = ""

    # Orígenes del frontend. Lista separada por comas en la variable de entorno.
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origins(self) -> list[str]:
        return [origen.strip() for origen in self.ALLOWED_ORIGINS.split(",") if origen.strip()]

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()