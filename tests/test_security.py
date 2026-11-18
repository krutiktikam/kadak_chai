import pytest

from app import config
from app.security import LoginLimiter, check_credentials


@pytest.fixture
def admin_creds(monkeypatch):
    monkeypatch.setattr(config, "ADMIN_USERNAME", "test-admin")
    monkeypatch.setattr(config, "ADMIN_PASSWORD", "test-pass")
    return "test-admin", "test-pass"


# 1. correct username and password -> True
def test_check_credentials_valid(admin_creds):
    username, password = admin_creds
    assert check_credentials(username, password) is True


# 2. right username, wrong password -> False
def test_check_credentials_wrong_password(admin_creds):
    username, _ = admin_creds
    assert check_credentials(username, "wrong-pass") is False


# 3. wrong username, right password -> False
def test_check_credentials_wrong_username(admin_creds):
    _, password = admin_creds
    assert check_credentials("wrong-admin", password) is False


# 4. non-ASCII input -> False, no exception
def test_check_credentials_non_ascii(admin_creds):
    assert check_credentials("ädmin", "pässword") is False


# 5. limiter: 4 failures with max 5 -> not blocked
def test_limiter_four_failures_not_blocked():
    limiter = LoginLimiter(max_failures=5, window_seconds=900)
    for _ in range(4):
        limiter.record_failure("10.0.0.1")
    assert limiter.is_blocked("10.0.0.1") is False


# 6. limiter: 5 failures -> blocked
def test_limiter_five_failures_blocked():
    limiter = LoginLimiter(max_failures=5, window_seconds=900)
    for _ in range(5):
        limiter.record_failure("10.0.0.1")
    assert limiter.is_blocked("10.0.0.1") is True


# 7. limiter: blocked IP A does not block IP B -> B not blocked
def test_limiter_isolated_per_ip():
    limiter = LoginLimiter(max_failures=5, window_seconds=900)
    for _ in range(5):
        limiter.record_failure("10.0.0.1")
    assert limiter.is_blocked("10.0.0.1") is True
    assert limiter.is_blocked("10.0.0.2") is False


# 8. limiter: after the window passes (fake clock) -> not blocked
def test_limiter_unblocks_after_window():
    now = [100.0]
    limiter = LoginLimiter(max_failures=5, window_seconds=60, clock=lambda: now[0])
    for _ in range(5):
        limiter.record_failure("10.0.0.1")
    assert limiter.is_blocked("10.0.0.1") is True

    now[0] = 161.0
    assert limiter.is_blocked("10.0.0.1") is False


# 9. limiter: reset after failures -> not blocked
def test_limiter_reset_clears_failures():
    limiter = LoginLimiter(max_failures=5, window_seconds=900)
    for _ in range(5):
        limiter.record_failure("10.0.0.1")
    assert limiter.is_blocked("10.0.0.1") is True

    limiter.reset("10.0.0.1")
    assert limiter.is_blocked("10.0.0.1") is False
