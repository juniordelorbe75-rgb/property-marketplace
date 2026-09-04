import warnings
from urllib.parse import urlsplit


KNOWN_SECRET_PLACEHOLDERS = {
    "change-me",
    "replace-me",
    "replace-with-a-long-random-secret",
    "secret",
}

def validate_secret_key(secret_key: str | None) -> str:
    if not secret_key:
        raise RuntimeError("SECRET_KEY environment variable is not set")
    if secret_key.strip().lower() in KNOWN_SECRET_PLACEHOLDERS:
        raise RuntimeError("SECRET_KEY still uses an unsafe placeholder value")
    if len(secret_key) < 16:
        raise RuntimeError("SECRET_KEY must be at least 16 characters")
    if len(secret_key) < 32:
        warnings.warn(
            "SECRET_KEY should be rotated to at least 32 random characters",
            RuntimeWarning,
            stacklevel=2,
        )
    return secret_key


def parse_cors_origins(value: str) -> list[str]:
    origins = list(dict.fromkeys(origin.strip().rstrip("/") for origin in value.split(",") if origin.strip()))
    if not origins:
        raise RuntimeError("CORS_ORIGINS must contain at least one origin")

    for origin in origins:
        parsed = urlsplit(origin)
        if origin == "*":
            raise RuntimeError("CORS_ORIGINS cannot use * when credentials are enabled")
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise RuntimeError(f"Invalid CORS origin: {origin}")
        if parsed.path or parsed.query or parsed.fragment:
            raise RuntimeError(f"CORS origin must not include a path: {origin}")

    return origins


def parse_admin_user_ids(value: str | None) -> set[int]:
    user_ids = set()
    for entry in (value or "").split(","):
        cleaned = entry.strip()
        if not cleaned:
            continue
        try:
            user_id = int(cleaned)
        except ValueError as error:
            raise RuntimeError(f"Invalid ADMIN_USER_IDS entry: {cleaned}") from error
        if user_id <= 0:
            raise RuntimeError(f"Invalid ADMIN_USER_IDS entry: {cleaned}")
        user_ids.add(user_id)
    return user_ids


def parse_boolean_setting(name: str, value: str | None, default: bool = False) -> bool:
    if value is None or not value.strip():
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "on"}:
        return True
    if normalized in {"0", "false", "no", "off"}:
        return False
    raise RuntimeError(f"{name} must be true or false")


def parse_trusted_hosts(value: str) -> list[str]:
    hosts = list(dict.fromkeys(host.strip().lower() for host in value.split(",") if host.strip()))
    if not hosts:
        raise RuntimeError("TRUSTED_HOSTS must contain at least one host")
    for host in hosts:
        if "://" in host or "/" in host or host == "*":
            raise RuntimeError(f"Invalid trusted host: {host}")
        if host.startswith(".") or host.endswith(".") or ".." in host:
            raise RuntimeError(f"Invalid trusted host: {host}")
    return hosts
