import json
import os
import secrets
from base64 import b64encode
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Lock
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request as UrlRequest, urlopen

from fastapi import HTTPException


@dataclass(frozen=True)
class Provider:
    label: str
    authorize_url: str
    token_url: str
    userinfo_url: str
    scope: str


PROVIDERS = {
    "google": Provider("Google", "https://accounts.google.com/o/oauth2/v2/auth", "https://oauth2.googleapis.com/token", "https://openidconnect.googleapis.com/v1/userinfo", "openid profile email"),
    "facebook": Provider("Facebook", "https://www.facebook.com/dialog/oauth", "https://graph.facebook.com/oauth/access_token", "https://graph.facebook.com/me?fields=id,name,email", "email public_profile"),
    "yahoo": Provider("Yahoo", "https://api.login.yahoo.com/oauth2/request_auth", "https://api.login.yahoo.com/oauth2/get_token", "https://api.login.yahoo.com/openid/v1/userinfo", "openid profile email"),
}

_lock = Lock()
_flows = {}
_codes = {}


def _clean(store, now):
    for key, value in list(store.items()):
        if value[-1] <= now:
            store.pop(key, None)


def provider_credentials(provider):
    prefix = provider.upper()
    return os.getenv(f"{prefix}_CLIENT_ID", "").strip(), os.getenv(f"{prefix}_CLIENT_SECRET", "").strip()


def enabled_providers():
    return [{"id": key, "name": item.label} for key, item in PROVIDERS.items() if all(provider_credentials(key))]


def provider_options():
    return [
        {
            "id": key,
            "name": item.label,
            "enabled": all(provider_credentials(key)),
        }
        for key, item in PROVIDERS.items()
    ]


def redirect_uri(provider):
    base = os.getenv("OAUTH_REDIRECT_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
    return f"{base}/auth/{provider}/callback"


def begin_flow(provider, return_to):
    config = PROVIDERS.get(provider)
    if config is None:
        raise HTTPException(404, "Unknown sign-in provider")
    client_id, client_secret = provider_credentials(provider)
    if not client_id or not client_secret:
        raise HTTPException(503, f"{config.label} sign-in is not configured")
    state = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    with _lock:
        _clean(_flows, now)
        _flows[state] = (provider, return_to, now + timedelta(minutes=10))
    url = f"{config.authorize_url}?{urlencode({'client_id': client_id, 'redirect_uri': redirect_uri(provider), 'response_type': 'code', 'scope': config.scope, 'state': state})}"
    return url, state


def consume_flow(provider, state):
    now = datetime.now(timezone.utc)
    with _lock:
        _clean(_flows, now)
        flow = _flows.pop(state, None)
    if flow is None or flow[0] != provider:
        raise HTTPException(400, "The sign-in request expired or is invalid")
    return flow[1]


def _json_request(url, *, data=None, access_token=None, basic_auth=None):
    body = urlencode(data).encode() if data is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    if access_token:
        headers["Authorization"] = f"Bearer {access_token}"
    if basic_auth:
        encoded = b64encode(f"{basic_auth[0]}:{basic_auth[1]}".encode()).decode()
        headers["Authorization"] = f"Basic {encoded}"
    try:
        with urlopen(UrlRequest(url, data=body, headers=headers), timeout=10) as response:
            return json.loads(response.read().decode())
    except (HTTPError, URLError, TimeoutError, ValueError) as error:
        raise HTTPException(502, "The sign-in provider could not be reached") from error


def fetch_profile(provider, code):
    config = PROVIDERS[provider]
    client_id, client_secret = provider_credentials(provider)
    token_data = {"code": code, "redirect_uri": redirect_uri(provider), "grant_type": "authorization_code"}
    basic_auth = (client_id, client_secret) if provider == "yahoo" else None
    if basic_auth is None:
        token_data.update({"client_id": client_id, "client_secret": client_secret})
    token = _json_request(config.token_url, data=token_data, basic_auth=basic_auth)
    if not token.get("access_token"):
        raise HTTPException(502, "The sign-in provider returned an invalid response")
    profile = _json_request(config.userinfo_url, access_token=token["access_token"])
    subject = str(profile.get("sub") or profile.get("id") or "").strip()
    email = str(profile.get("email") or "").strip().lower()
    name = str(profile.get("name") or email.split("@")[0] or "Marketplace user").strip()
    verified = bool(email) if provider == "facebook" else profile.get("email_verified") is True
    if not subject or not email or not verified:
        raise HTTPException(400, "A verified email address is required for sign-in")
    return subject, email, name[:100]


def create_login_code(user_id):
    code = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    with _lock:
        _clean(_codes, now)
        _codes[code] = (user_id, now + timedelta(minutes=2))
    return code


def consume_login_code(code):
    now = datetime.now(timezone.utc)
    with _lock:
        _clean(_codes, now)
        entry = _codes.pop(code, None)
    if entry is None:
        raise HTTPException(400, "The sign-in code expired or was already used")
    return entry[0]
