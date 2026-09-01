from collections import deque
from math import ceil
from threading import Lock
from time import monotonic


MAX_FAILED_ATTEMPTS = 5
ATTEMPT_WINDOW_SECONDS = 15 * 60
MAX_TRACKED_KEYS = 10_000

_failed_attempts: dict[str, deque[float]] = {}
_lock = Lock()


def _key(client_address: str, email: str) -> str:
    return f"{client_address}|{email.strip().lower()}"


def _prune(attempts: deque[float], now: float) -> None:
    cutoff = now - ATTEMPT_WINDOW_SECONDS
    while attempts and attempts[0] <= cutoff:
        attempts.popleft()


def login_retry_after(client_address: str, email: str) -> int | None:
    key = _key(client_address, email)
    now = monotonic()

    with _lock:
        attempts = _failed_attempts.get(key)
        if attempts is None:
            return None

        _prune(attempts, now)
        if not attempts:
            _failed_attempts.pop(key, None)
            return None
        if len(attempts) < MAX_FAILED_ATTEMPTS:
            return None

        return max(1, ceil(ATTEMPT_WINDOW_SECONDS - (now - attempts[0])))


def record_login_failure(client_address: str, email: str) -> None:
    key = _key(client_address, email)
    now = monotonic()

    with _lock:
        if key not in _failed_attempts and len(_failed_attempts) >= MAX_TRACKED_KEYS:
            oldest_key = next(iter(_failed_attempts))
            _failed_attempts.pop(oldest_key, None)
        attempts = _failed_attempts.setdefault(key, deque())
        _prune(attempts, now)
        attempts.append(now)


def clear_login_failures(client_address: str, email: str) -> None:
    with _lock:
        _failed_attempts.pop(_key(client_address, email), None)


def reset_login_throttle() -> None:
    """Clear process-local state for application lifecycle hooks and tests."""
    with _lock:
        _failed_attempts.clear()
