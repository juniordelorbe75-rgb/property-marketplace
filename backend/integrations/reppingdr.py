from datetime import datetime

from backend.feed_models import ListingFeedBatch


STATUS_MAP = {
    "available": "active",
    "pre-sale": "active",
    "under-construction": "active",
    "reserved": "pending",
    "sold": "sold",
}


def build_reppingdr_batch(
    properties_payload: dict,
    zones_payload: dict,
    retrieved_at: datetime,
    permission_url: str,
    permission_approved: bool = False,
) -> ListingFeedBatch:
    if not permission_approved:
        raise PermissionError(
            "Written ReppingDR republication permission must be approved before import"
        )

    zones = {
        zone["id"]: zone
        for zone in zones_payload.get("zones", [])
        if isinstance(zone, dict) and zone.get("id")
    }
    records = []
    for item in properties_payload.get("properties", []):
        zone = zones.get(item.get("zone"), {})
        status = STATUS_MAP.get(item.get("status"))
        if not status:
            continue
        if not zone.get("province"):
            raise ValueError(f"ReppingDR listing {item.get('id')} has no recognized zone province")
        slug = str(item.get("slug") or "").strip()
        records.append({
            "external_id": str(item["id"]),
            "source_url": f"https://www.reppingdr.com/properties/{slug}",
            "title": item["title"],
            "description": item.get("aiDescription") or "",
            "listing_type": "sale",
            "status": status,
            "price": item["price"],
            "currency": item["currency"],
            "country_code": "DO",
            "province": zone.get("province") or "",
            "municipality": zone.get("nameEs") or zone.get("name") or item.get("zone") or "",
            "sector": "",
            "property_type": item["type"],
            "bedrooms": item.get("bedrooms"),
            "bathrooms": item.get("bathrooms"),
            "area_sqm": item.get("sqm"),
            "image_urls": item.get("images") or ([item["thumbnail"]] if item.get("thumbnail") else []),
            "amenities": item.get("amenities") or [],
            "updated_at": retrieved_at,
        })

    return ListingFeedBatch.model_validate({
        "source": {
            "source_key": "reppingdr",
            "name": "ReppingDR",
            "country_code": "DO",
            "license_name": "Written commercial republication agreement",
            "license_url": permission_url,
            "attribution": "Property data courtesy of ReppingDR and its participating developers",
            "permits_commercial_display": True,
        },
        "retrieved_at": retrieved_at,
        "records": records,
    })
