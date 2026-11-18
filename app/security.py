import hmac
import time
from collections import defaultdict, deque

from app import config


def check_credentials(username: str, password: str) -> bool:
    """True only if BOTH match. Both comparisons always run (no early exit).
    We compare bytes because compare_digest raises TypeError on non-ASCII str."""
    user_ok = hmac.compare_digest(username.encode(), config.ADMIN_USERNAME.encode())
    pass_ok = hmac.compare_digest(password.encode(), config.ADMIN_PASSWORD.encode())
    return user_ok and pass_ok


class LoginLimiter:
    """Blocks a key (an IP address) after too many recent failures."""

    def __init__(self, max_failures=5, window_seconds=900, clock=time.monotonic):
        self.max_failures = max_failures
        self.window = window_seconds
        self.clock = clock  # injectable so tests don't have to sleep
        self._failures: dict[str, deque] = defaultdict(deque)

    def _recent(self, key: str) -> deque:
        """Drop failures older than the window, return what is left."""
        times = self._failures[key]
        cutoff = self.clock() - self.window
        while times and times[0] <= cutoff:
            times.popleft()
        if not times:
            self._failures.pop(key, None)  # don't let the dict grow forever
        return times

    def is_blocked(self, key: str) -> bool:
        return len(self._recent(key)) >= self.max_failures

    def record_failure(self, key: str) -> None:
        self._recent(key)
        self._failures[key].append(self.clock())

    def reset(self, key: str) -> None:
        """Call after a successful login."""
        self._failures.pop(key, None)


login_limiter = LoginLimiter()
