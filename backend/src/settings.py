from pydantic_settings import BaseSettings
from typing import Optional
from pathlib import Path
from dotenv import load_dotenv

root_env = Path(__file__).parent.parent.parent / ".env"
if root_env.exists():
    load_dotenv(root_env)


class Settings(BaseSettings):
    # === Application ===
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    ENVIRONMENT: str = "development"

    # === Database ===
    DB_HOST: str = "postgres"
    DB_PORT: int = 5432
    DB_NAME: str = "taxi_agent"
    DB_USER: str = "user"
    DB_PASSWORD: str = "password"
    DB_POOL_MIN: int = 5
    DB_POOL_MAX: int = 20

    # === OpenRouter ===
    OPENROUTER_API_KEY: str
    OPENROUTER_MODEL: str = "meta-llama/llama-3.1-8b-instruct:free"

    # === 2GIS ===
    DGIS_API_KEY: str

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
