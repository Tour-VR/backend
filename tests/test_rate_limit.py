from __future__ import annotations

from app.core.rate_limit import LoginRateLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def test_blocks_after_max_failures() -> None:
    limiter = LoginRateLimiter(max_failures=5, window_seconds=900, clock=FakeClock())

    for _ in range(4):
        limiter.register_failure("ip|user")
    assert limiter.is_blocked("ip|user") is False

    limiter.register_failure("ip|user")
    assert limiter.is_blocked("ip|user") is True
    assert limiter.is_blocked("ip|outro") is False


def test_unblocks_after_window() -> None:
    clock = FakeClock()
    limiter = LoginRateLimiter(max_failures=5, window_seconds=900, clock=clock)

    for _ in range(5):
        limiter.register_failure("ip|user")
    assert limiter.is_blocked("ip|user") is True

    clock.now += 901
    assert limiter.is_blocked("ip|user") is False


def test_reset_clears_failures() -> None:
    limiter = LoginRateLimiter(max_failures=5, window_seconds=900, clock=FakeClock())

    for _ in range(5):
        limiter.register_failure("ip|user")
    limiter.reset("ip|user")

    assert limiter.is_blocked("ip|user") is False


def test_clear_removes_all_keys() -> None:
    limiter = LoginRateLimiter(max_failures=1, window_seconds=900, clock=FakeClock())

    limiter.register_failure("a")
    limiter.register_failure("b")
    limiter.clear()

    assert limiter.is_blocked("a") is False
    assert limiter.is_blocked("b") is False
