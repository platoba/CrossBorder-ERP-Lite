"""Rate limiter tests."""

import pytest
import time

from app.middleware.rate_limit import RateLimiter


class TestRateLimiter:
    def test_allows_within_limit(self):
        rl = RateLimiter(requests_per_minute=60, burst=5)
        for _ in range(5):
            assert rl.allow("client1") is True

    def test_blocks_after_burst(self):
        rl = RateLimiter(requests_per_minute=60, burst=3)
        for _ in range(3):
            rl.allow("client1")
        assert rl.allow("client1") is False

    def test_separate_clients(self):
        rl = RateLimiter(requests_per_minute=60, burst=2)
        rl.allow("a")
        rl.allow("a")
        assert rl.allow("a") is False
        assert rl.allow("b") is True  # Different client

    def test_remaining_tokens(self):
        rl = RateLimiter(requests_per_minute=60, burst=5)
        assert rl.remaining("x") == 5
        rl.allow("x")
        assert rl.remaining("x") == 4

    def test_reset_single_key(self):
        rl = RateLimiter(requests_per_minute=60, burst=2)
        rl.allow("a")
        rl.allow("a")
        rl.reset("a")
        assert rl.allow("a") is True

    def test_reset_all(self):
        rl = RateLimiter(requests_per_minute=60, burst=2)
        rl.allow("a")
        rl.allow("b")
        rl.reset()
        assert rl.remaining("a") == 2
        assert rl.remaining("b") == 2

    def test_refill_over_time(self):
        rl = RateLimiter(requests_per_minute=600, burst=3)  # 10/sec
        rl.allow("t")
        rl.allow("t")
        rl.allow("t")
        assert rl.allow("t") is False
        # Simulate time passing by modifying internal state
        rl._buckets["t"]["last"] -= 1  # 1 second ago
        assert rl.allow("t") is True  # Should have refilled
