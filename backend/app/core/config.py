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
    ALPHA_VANTAGE_API_KEY: str = ""

    # Auth settings
    jwt_secret: str = Field("dev-secret-change-in-prod", alias="JWT_SECRET")
    admin_username: str = Field("admin", alias="ADMIN_USERNAME")
    admin_password_hash: str = Field("", alias="ADMIN_PASSWORD_HASH")

    # CORS / cookie settings
    frontend_url: str = Field("http://localhost:5173", alias="FRONTEND_URL")
    cookie_samesite: str = Field("lax", alias="COOKIE_SAMESITE")

    # Alert notification channels
    telegram_bot_token: str = Field("", alias="TELEGRAM_BOT_TOKEN")
    telegram_chat_id: str = Field("", alias="TELEGRAM_CHAT_ID")
    discord_webhook_url: str = Field("", alias="DISCORD_WEBHOOK_URL")

    # LLM settings — disabled by default; set OPENROUTER_API_KEY to enable
    # OpenRouter provides free model access (meta-llama, deepseek, qwen)
    openrouter_api_key: str = Field("", alias="OPENROUTER_API_KEY")
    openrouter_model: str = Field("meta-llama/llama-4-scout:free", alias="OPENROUTER_MODEL")
    llm_enabled: bool = Field(False, alias="LLM_ENABLED")


settings = Settings()
