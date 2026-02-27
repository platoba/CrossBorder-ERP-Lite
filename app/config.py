"""Configuration."""

from functools import lru_cache
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "CrossBorder-ERP-Lite"
    debug: bool = False
    secret_key: str = "change-me"

    database_url: str = "postgresql+asyncpg://erp:erp_password@localhost:5432/erp_db"
    database_url_sync: str = "postgresql://erp:erp_password@localhost:5432/erp_db"
    redis_url: str = "redis://localhost:6379/0"

    # Platform API keys
    amazon_client_id: str = ""
    amazon_client_secret: str = ""
    amazon_refresh_token: str = ""
    amazon_marketplace: str = "ATVPDKIKX0DER"  # US

    shopify_shop_url: str = ""
    shopify_access_token: str = ""

    ebay_app_id: str = ""
    ebay_cert_id: str = ""

    # Auth
    admin_email: str = "admin@example.com"
    admin_password: str = "changeme123"
    jwt_expire_minutes: int = 1440

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


@lru_cache
def get_settings() -> Settings:
    return Settings()
