"""Config tests."""

import pytest

from app.config import Settings, get_settings


class TestSettings:
    def test_default_values(self):
        s = Settings()
        assert s.app_name == "CrossBorder-ERP-Lite"
        assert s.debug is False
        assert s.jwt_expire_minutes == 1440
        assert s.admin_email == "admin@example.com"

    def test_get_settings_cached(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2  # lru_cache

    def test_database_url(self):
        s = Settings()
        assert "postgresql" in s.database_url

    def test_platform_defaults(self):
        s = Settings()
        assert s.amazon_marketplace == "ATVPDKIKX0DER"
        assert s.amazon_client_id == ""
