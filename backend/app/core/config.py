"""
Application settings loaded from environment variables.

Uses pydantic-settings for type-safe configuration with .env file support.
API keys are never committed to source control — see .env.example for required vars.
"""
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "sqlite+aiosqlite:///./dev.db"
    FINNHUB_API_KEY: str = ""
    COINGECKO_API_KEY: str = ""

    # Auth settings
    jwt_secret: str = Field("dev-secret-change-in-prod", alias="JWT_SECRET")
    admin_username: str = Field("admin", alias="ADMIN_USERNAME")
    admin_password_hash: str = Field("", alias="ADMIN_PASSWORD_HASH")

    # CORS / cookie settings
    frontend_url: str = Field("http://localhost:5173", alias="FRONTEND_URL")
    cookie_samesite: str = Field("lax", alias="COOKIE_SAMESITE")


settings = Settings()
