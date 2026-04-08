"""
Application settings loaded from environment variables.

Uses pydantic-settings for type-safe configuration with .env file support.
API keys are never committed to source control — see .env.example for required vars.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"
    FINNHUB_API_KEY: str = ""
    COINGECKO_API_KEY: str = ""


settings = Settings()
