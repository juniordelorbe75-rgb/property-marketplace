import os
import warnings
from email.utils import parseaddr
from urllib.parse import parse_qs, urlsplit


KNOWN_SECRET_PLACEHOLDERS = {
    "change-me",
    "replace-me",
    "replace-with-a-long-random-secret",
    "secret",
}

ALLOWED_APP_ENVIRONMENTS = {"development", "test", "production"}


def parse_app_environment(value: str | None) -> str:
    environment = "development" if value is None else value.strip().lower()
    if environment not in ALLOWED_APP_ENVIRONMENTS:
        raise RuntimeError(
            "APP_ENV must be development, test, or production"
        )
    return environment


def api_documentation_paths(environment: str) -> dict[str, str | None]:
    if parse_app_environment(environment) == "production":
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
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


def parse_bounded_integer_setting(
    name: str,
    value: str | None,
    *,
    default: int,
    minimum: int,
    maximum: int,
) -> int:
    if value is None or not value.strip():
        return default
    try:
        parsed = int(value)
    except ValueError as error:
        raise RuntimeError(f"{name} must be a whole number") from error
    if not minimum <= parsed <= maximum:
        raise RuntimeError(f"{name} must be between {minimum} and {maximum}")
    return parsed


def database_engine_options(database_url: str, settings=None) -> dict:
    settings = os.environ if settings is None else settings
    options = {"pool_pre_ping": True, "hide_parameters": True}
    if database_url.startswith("sqlite"):
        return options
    if not database_url.startswith("postgresql"):
        return options

    options.update({
        "pool_size": parse_bounded_integer_setting(
            "DATABASE_POOL_SIZE", settings.get("DATABASE_POOL_SIZE"),
            default=5, minimum=1, maximum=50,
        ),
        "max_overflow": parse_bounded_integer_setting(
            "DATABASE_MAX_OVERFLOW", settings.get("DATABASE_MAX_OVERFLOW"),
            default=10, minimum=0, maximum=100,
        ),
        "pool_timeout": parse_bounded_integer_setting(
            "DATABASE_POOL_TIMEOUT_SECONDS", settings.get("DATABASE_POOL_TIMEOUT_SECONDS"),
            default=10, minimum=1, maximum=60,
        ),
        "pool_recycle": parse_bounded_integer_setting(
            "DATABASE_POOL_RECYCLE_SECONDS", settings.get("DATABASE_POOL_RECYCLE_SECONDS"),
            default=300, minimum=30, maximum=3600,
        ),
        "pool_use_lifo": True,
        "connect_args": {
            "connect_timeout": parse_bounded_integer_setting(
                "DATABASE_CONNECT_TIMEOUT_SECONDS",
                settings.get("DATABASE_CONNECT_TIMEOUT_SECONDS"),
                default=10, minimum=1, maximum=60,
            ),
            "application_name": "HabitaRD API",
        },
    })
    return options


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


def validate_production_environment(settings=None) -> None:
    settings = os.environ if settings is None else settings
    environment = parse_app_environment(settings.get("APP_ENV"))
    if environment != "production":
        return

    from backend.image_storage import image_storage_mode, validate_object_storage_settings

    required = (
        "DATABASE_URL", "SECRET_KEY", "CORS_ORIGINS", "TRUSTED_HOSTS",
        "FRONTEND_URL", "SMTP_HOST", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM",
    )
    missing = [name for name in required if not settings.get(name, "").strip()]
    if missing:
        raise RuntimeError(f"Missing production settings: {', '.join(missing)}")

    if not parse_boolean_setting("FORCE_HTTPS", settings.get("FORCE_HTTPS")):
        raise RuntimeError("FORCE_HTTPS must be true in production")
    if not parse_boolean_setting("SMTP_USE_TLS", settings.get("SMTP_USE_TLS")):
        raise RuntimeError("SMTP_USE_TLS must be true in production")
    if image_storage_mode(settings) != "s3":
        raise RuntimeError("PROPERTY_IMAGE_STORAGE must be s3 in production")
    validate_object_storage_settings(settings)
    parse_bounded_integer_setting(
        "SMTP_PORT", settings.get("SMTP_PORT"), default=587, minimum=1, maximum=65535
    )
    parse_bounded_integer_setting(
        "SMTP_TIMEOUT_SECONDS", settings.get("SMTP_TIMEOUT_SECONDS"),
        default=10, minimum=1, maximum=60,
    )
    parse_bounded_integer_setting(
        "ACCESS_TOKEN_EXPIRE_MINUTES",
        settings.get("ACCESS_TOKEN_EXPIRE_MINUTES"),
        default=60,
        minimum=5,
        maximum=60,
    )
    if not parse_admin_user_ids(settings.get("ADMIN_USER_IDS")):
        raise RuntimeError("ADMIN_USER_IDS must contain at least one administrator in production")

    frontend = urlsplit(settings["FRONTEND_URL"].strip())
    if frontend.scheme != "https" or not frontend.netloc or frontend.path not in {"", "/"}:
        raise RuntimeError("FRONTEND_URL must be an HTTPS origin in production")
    for origin in parse_cors_origins(settings["CORS_ORIGINS"]):
        if urlsplit(origin).scheme != "https":
            raise RuntimeError("Every production CORS origin must use HTTPS")
    hosts = parse_trusted_hosts(settings["TRUSTED_HOSTS"])
    if any(host in {"localhost", "127.0.0.1"} for host in hosts):
        raise RuntimeError("Production TRUSTED_HOSTS cannot use local development hosts")
    database_url = settings["DATABASE_URL"]
    if not database_url.startswith("postgresql+psycopg://"):
        raise RuntimeError(
            "Production DATABASE_URL must use PostgreSQL with the psycopg driver"
        )
    ssl_mode = parse_qs(urlsplit(database_url).query).get("sslmode", [""])[0].lower()
    if ssl_mode not in {"require", "verify-ca", "verify-full"}:
        raise RuntimeError("Production DATABASE_URL must require encrypted PostgreSQL transport")
    database_engine_options(database_url, settings)
    if "example." in settings["SMTP_FROM"].lower():
        raise RuntimeError("SMTP_FROM must use the verified HabitaRD sender address")
    sender_header = settings["SMTP_FROM"].strip()
    _sender_name, sender_address = parseaddr(sender_header)
    if (
        "\r" in sender_header
        or "\n" in sender_header
        or "@" not in sender_address
    ):
        raise RuntimeError("SMTP_FROM must contain one valid sender address")
