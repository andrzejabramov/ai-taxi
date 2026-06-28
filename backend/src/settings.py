from pydantic_settings import BaseSettings
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

backend_env = Path(__file__).parent.parent / ".env"
if backend_env.exists():
    load_dotenv(backend_env)


class Settings(BaseSettings):
    # === Application ===
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # === Database (только строка подключения, всё остальное в docker-compose) ===
    DATABASE_URL: str  # обязательное, читается из environment

    # === Database Pool ===
    DB_POOL_MIN: int = 5
    DB_POOL_MAX: int = 20

    # === OpenRouter ===
    OPENROUTER_API_KEY: str
    OPENROUTER_TIMEOUT: int = 30
    OPENROUTER_MODELS_CACHE_TTL: int = 3600
    OPENROUTER_MAX_MODELS: int = 10

    # === 2GIS ===
    DGIS_API_KEY: Optional[str] = None

    # === Yandex Geocoder ===
    YANDEX_GEOCODER_API_KEY: Optional[str] = None

    # === Yandex SpeechKit ===
    YANDEX_SPEECHKIT_API_KEY: Optional[str] = None

    @property
    def use_2gis(self) -> bool:
        return bool(self.DGIS_API_KEY)

    @property
    def use_yandex_geocoder(self) -> bool:
        return bool(self.YANDEX_GEOCODER_API_KEY)

    class Config:
        case_sensitive = True


settings = Settings()
