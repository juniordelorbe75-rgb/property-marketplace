import os
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def _render_database_url(value: str) -> str:
    if value.startswith("postgres://"):
        value = "postgresql://" + value.removeprefix("postgres://")
    if value.startswith("postgresql://"):
        value = "postgresql+psycopg://" + value.removeprefix("postgresql://")

    parsed = urlsplit(value)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.setdefault("sslmode", "require")
    return urlunsplit((parsed.scheme, parsed.netloc, parsed.path, urlencode(query), ""))


def configure_environment() -> None:
    render_database_url = os.getenv("RENDER_DATABASE_URL", "").strip()
    if render_database_url:
        os.environ["DATABASE_URL"] = _render_database_url(render_database_url)

    hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip().lower()
    if hostname:
        public_origin = f"https://{hostname}"
        os.environ.setdefault("TRUSTED_HOSTS", hostname)
        os.environ.setdefault("OAUTH_REDIRECT_BASE_URL", public_origin)


def main() -> None:
    configure_environment()

    from backend.db import apply_schema_updates

    apply_schema_updates()

    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "10000")),
        proxy_headers=True,
        forwarded_allow_ips=os.getenv("TRUSTED_PROXY_IPS", "127.0.0.1"),
    )


if __name__ == "__main__":
    main()
