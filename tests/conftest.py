"""Test fixtures."""

import asyncio
from typing import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base, get_db
from app.main import app

# Use SQLite for tests (no external DB needed for unit tests)
TEST_DB_URL = "sqlite+aiosqlite:///./test.db"

test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_session() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db


def _reset_rate_limiter():
    """Reset the in-memory rate limiter between tests to avoid 429s."""
    for mw in app.user_middleware:
        if hasattr(mw, "cls") and mw.cls.__name__ == "RateLimitMiddleware":
            break
    # Walk the middleware stack to find the rate limiter instance
    cur = app.middleware_stack
    while cur is not None:
        if hasattr(cur, "limiter"):
            cur.limiter.reset()
            return
        cur = getattr(cur, "app", None)


@pytest_asyncio.fixture(autouse=True)
async def reset_rate_limits():
    """Auto-reset rate limiter before each test."""
    _reset_rate_limiter()
    yield


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
