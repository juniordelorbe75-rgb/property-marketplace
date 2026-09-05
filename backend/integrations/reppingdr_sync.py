import json
import os
from datetime import datetime, timezone
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from sqlalchemy.orm import Session

from backend.db_models.external_listing import ListingSourceDB
from backend.integrations.reppingdr import build_reppingdr_batch
from backend.repositories.external_listing_repository import import_feed_batch


BASE_URL = "https://reppingdr.com/api/v1"
MAX_RESPONSE_BYTES = 12 * 1024 * 1024
MAX_PAGES = 200


def _fetch_json(url: str, api_key: str) -> dict:
    request = Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "Mercado-de-Porpiedades/1.0",
            "X-Api-Key": api_key,
        },
    )
    with urlopen(request, timeout=30) as response:
        payload = response.read(MAX_RESPONSE_BYTES + 1)
    if len(payload) > MAX_RESPONSE_BYTES:
        raise ValueError("Provider response exceeded the safety limit")
    value = json.loads(payload)
    if not isinstance(value, dict):
        raise ValueError("Provider returned an unexpected response")
    if value.get("error"):
        raise RuntimeError("Provider rejected the request")
    return value


def sync_reppingdr(
    session: Session,
    source: ListingSourceDB,
    *,
    fetch_json=_fetch_json,
    api_key: str | None = None,
) -> dict[str, int]:
    if source.source_key != "reppingdr":
        raise ValueError("This synchronization is only valid for the ReppingDR source")
    if not source.approved or source.approval_status != "approved" or not source.permission_document_url:
        raise PermissionError("ReppingDR must have recorded written republication approval")
    now = datetime.now(timezone.utc)
    expires_at = source.permission_expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            raise PermissionError("ReppingDR republication approval has expired")

    secret = api_key or os.getenv("REPPINGDR_API_KEY")
    if not secret:
        raise RuntimeError("REPPINGDR_API_KEY is not configured")

    zones = fetch_json(f"{BASE_URL}/zones", secret)
    properties = []
    page = 1
    while page <= MAX_PAGES:
        query = urlencode({"page": page, "limit": 100})
        payload = fetch_json(f"{BASE_URL}/properties?{query}", secret)
        page_records = payload.get("properties")
        if not isinstance(page_records, list):
            raise ValueError("Provider properties response is malformed")
        properties.extend(page_records)
        if not payload.get("hasMore"):
            break
        page += 1
    else:
        raise RuntimeError("Provider pagination exceeded the configured safety limit")

    batch = build_reppingdr_batch(
        {"properties": properties},
        zones,
        now,
        source.permission_document_url,
        permission_approved=True,
    )
    return import_feed_batch(session, batch)
