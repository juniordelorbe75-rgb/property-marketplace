from collections import deque
from math import ceil
from threading import Lock
from time import monotonic


MAX_TRACKED_KEYS = 20_000

_attempts: dict[str, deque[float]] = {}
_lock = Lock()


def consume_rate_limit(
    action: str,
    client_address: str,
    *,
    limit: int,
    window_seconds: int,
) -> int | None:
    """Record an attempt and return Retry-After seconds when the limit is exceeded."""
    key = f"{action}|{client_address}"
    now = monotonic()
    cutoff = now - window_seconds

    with _lock:
        if key not in _attempts and len(_attempts) >= MAX_TRACKED_KEYS:
            _attempts.pop(next(iter(_attempts)), None)
        attempts = _attempts.setdefault(key, deque())
        while attempts and attempts[0] <= cutoff:
            attempts.popleft()

        if len(attempts) >= limit:
            return max(1, ceil(window_seconds - (now - attempts[0])))

        attempts.append(now)
        return None


def reset_request_throttles() -> None:
    """Clear process-local counters for application lifecycle hooks and tests."""
    with _lock:
        _attempts.clear()


def retry_after_detail(message: str, retry_after: int) -> str:
    minutes = max(1, ceil(retry_after / 60))
    unit = "minute" if minutes == 1 else "minutes"
    return f"{message} Try again in about {minutes} {unit}."
