from collections import deque
from math import ceil
from threading import Lock
from time import monotonic


MAX_FAILED_ATTEMPTS = 5
MAX_ACCOUNT_FAILED_ATTEMPTS = 10
MAX_CLIENT_FAILED_ATTEMPTS = 25
ATTEMPT_WINDOW_SECONDS = 15 * 60
MAX_TRACKED_KEYS = 30_000

_failed_attempts: dict[str, deque[float]] = {}
_lock = Lock()


def _normalized_email(email: str) -> str:
    return email.strip().lower()


def _keys(client_address: str, email: str) -> tuple[str, str, str]:
    normalized_email = _normalized_email(email)
    return (
        f"pair|{client_address}|{normalized_email}",
        f"account|{normalized_email}",
        f"client|{client_address}",
    )


def _prune(attempts: deque[float], now: float) -> None:
    cutoff = now - ATTEMPT_WINDOW_SECONDS
    while attempts and attempts[0] <= cutoff:
        attempts.popleft()


def login_retry_after(client_address: str, email: str) -> int | None:
    pair_key, account_key, client_key = _keys(client_address, email)
    now = monotonic()

    with _lock:
        retry_after = []
        for key, limit in (
            (pair_key, MAX_FAILED_ATTEMPTS),
            (account_key, MAX_ACCOUNT_FAILED_ATTEMPTS),
            (client_key, MAX_CLIENT_FAILED_ATTEMPTS),
        ):
            attempts = _failed_attempts.get(key)
            if attempts is None:
                continue
            _prune(attempts, now)
            if not attempts:
                _failed_attempts.pop(key, None)
                continue
            if len(attempts) >= limit:
                retry_after.append(
                    max(1, ceil(ATTEMPT_WINDOW_SECONDS - (now - attempts[0])))
                )

        return max(retry_after, default=None)


def record_login_failure(client_address: str, email: str) -> None:
    now = monotonic()

    with _lock:
        for key in _keys(client_address, email):
            if key not in _failed_attempts and len(_failed_attempts) >= MAX_TRACKED_KEYS:
                oldest_key = next(iter(_failed_attempts))
                _failed_attempts.pop(oldest_key, None)
            attempts = _failed_attempts.setdefault(key, deque())
            _prune(attempts, now)
            attempts.append(now)


def clear_login_failures(client_address: str, email: str) -> None:
    pair_key, account_key, _client_key = _keys(client_address, email)
    with _lock:
        _failed_attempts.pop(pair_key, None)
        _failed_attempts.pop(account_key, None)


def reset_login_throttle() -> None:
    """Clear process-local state for application lifecycle hooks and tests."""
    with _lock:
        _failed_attempts.clear()
