"""Auth service tests."""

import pytest
from datetime import timedelta

from app.services.auth import (
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)


class TestPasswordHashing:
    def test_hash_and_verify(self):
        hashed = hash_password("secret123")
        assert verify_password("secret123", hashed)

    def test_wrong_password(self):
        hashed = hash_password("correct")
        assert not verify_password("wrong", hashed)

    def test_different_hashes(self):
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2  # bcrypt uses random salt


class TestJWT:
    def test_create_and_decode(self):
        token = create_access_token({"sub": "admin@test.com", "role": "admin"})
        payload = decode_token(token)
        assert payload["sub"] == "admin@test.com"
        assert payload["role"] == "admin"

    def test_token_has_expiry(self):
        token = create_access_token({"sub": "test"})
        payload = decode_token(token)
        assert "exp" in payload
        assert "iat" in payload

    def test_custom_expiry(self):
        token = create_access_token(
            {"sub": "test"},
            expires_delta=timedelta(minutes=5),
        )
        payload = decode_token(token)
        assert payload["exp"] - payload["iat"] <= 300 + 1

    def test_invalid_token_raises(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_token("invalid.token.here")
        assert exc_info.value.status_code == 401
