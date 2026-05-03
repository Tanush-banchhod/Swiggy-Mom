from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Swiggy MCP
    swiggy_client_id: str = ""
    swiggy_client_secret: str = ""
    swiggy_redirect_uri: str = "http://localhost:8000/auth/callback"
    swiggy_food_mcp_url: str = "https://mcp.swiggy.com/food"
    swiggy_instamart_mcp_url: str = "https://mcp.swiggy.com/im"

    # Swiggy OAuth endpoints (discovered from well-known)
    swiggy_auth_url: str = "https://auth.swiggy.com/oauth2/auth"
    swiggy_token_url: str = "https://auth.swiggy.com/oauth2/token"

    # Database
    database_url: str = "postgresql+asyncpg://swiggymom:swiggymom@localhost:5432/swiggymom"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-me-in-production"

    # Firebase
    fcm_server_key: str = ""

    # Optional
    weather_api_key: str = ""
    sentry_dsn: str = ""

    # Runtime
    environment: str = "development"
    log_level: str = "INFO"

    # Feature flags
    feature_instamart: bool = False
    feature_weather_scoring: bool = False
    feature_weekly_report: bool = True
    feature_cheat_mode: bool = True
    feature_variety_enforcement: bool = True
    feature_skip_learning: bool = True

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
