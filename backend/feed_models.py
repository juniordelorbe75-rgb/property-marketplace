from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.location_data import normalize_dominican_province, normalize_location_part


class ListingFeedSource(BaseModel):
    source_key: str = Field(pattern=r"^[a-z0-9][a-z0-9_-]{1,63}$")
    name: str = Field(min_length=2, max_length=150)
    country_code: str = Field(min_length=2, max_length=2)
    license_name: str = Field(min_length=2, max_length=150)
    license_url: str = Field(max_length=1000)
    attribution: str = Field(min_length=2, max_length=300)
    permits_commercial_display: bool

    @field_validator("country_code")
    @classmethod
    def normalize_country_code(cls, value: str) -> str:
        return value.upper()

    @field_validator("license_url")
    @classmethod
    def validate_license_url(cls, value: str) -> str:
        parsed = urlsplit(value.strip())
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("License URL must be a valid HTTPS URL")
        return value.strip()

    @model_validator(mode="after")
    def require_display_rights(self):
        if not self.permits_commercial_display:
            raise ValueError("Source does not permit commercial listing display")
        return self


class ListingFeedRecord(BaseModel):
    external_id: str = Field(min_length=1, max_length=200)
    source_url: str = Field(max_length=2000)
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=5000)
    listing_type: Literal["sale", "rent"]
    status: Literal["active", "pending", "sold", "rented", "withdrawn"]
    price: float = Field(gt=0)
    currency: str = Field(min_length=3, max_length=3)
    country_code: str = Field(min_length=2, max_length=2)
    province: str = Field(default="", max_length=100)
    municipality: str = Field(default="", max_length=100)
    sector: str = Field(default="", max_length=100)
    property_type: str = Field(min_length=2, max_length=100)
    bedrooms: int | None = Field(default=None, ge=0, le=100)
    bathrooms: float | None = Field(default=None, ge=0, le=100)
    area_sqm: float | None = Field(default=None, ge=0, le=100_000_000)
    image_urls: list[str] = Field(default_factory=list, max_length=30)
    amenities: list[str] = Field(default_factory=list, max_length=100)
    listed_at: datetime | None = None
    updated_at: datetime

    @field_validator("source_url")
    @classmethod
    def validate_source_url(cls, value: str) -> str:
        parsed = urlsplit(value.strip())
        if parsed.scheme != "https" or not parsed.netloc:
            raise ValueError("Source URL must be a valid HTTPS URL")
        return value.strip()

    @field_validator("country_code", "currency")
    @classmethod
    def normalize_codes(cls, value: str) -> str:
        return value.upper()

    @field_validator("province")
    @classmethod
    def validate_province(cls, value: str, info) -> str:
        country_code = info.data.get("country_code")
        return normalize_dominican_province(value) if country_code == "DO" else normalize_location_part(value)

    @field_validator("municipality", "sector")
    @classmethod
    def normalize_location_parts(cls, value: str) -> str:
        return normalize_location_part(value)

    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, values: list[str]) -> list[str]:
        cleaned = []
        for value in values:
            parsed = urlsplit(value.strip())
            if parsed.scheme != "https" or not parsed.netloc:
                raise ValueError("Feed images must use valid HTTPS URLs")
            if value.strip() not in cleaned:
                cleaned.append(value.strip())
        return cleaned

    @field_validator("amenities")
    @classmethod
    def normalize_amenities(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(normalize_location_part(value) for value in values if value.strip()))


class ListingFeedBatch(BaseModel):
    source: ListingFeedSource
    retrieved_at: datetime
    records: list[ListingFeedRecord] = Field(max_length=10_000)

    @model_validator(mode="after")
    def validate_batch_identity(self):
        seen = set()
        for record in self.records:
            if record.country_code != self.source.country_code:
                raise ValueError("Record country does not match its source")
            if record.external_id in seen:
                raise ValueError(f"Duplicate external listing ID: {record.external_id}")
            if record.updated_at > self.retrieved_at:
                raise ValueError("Listing update time cannot be after feed retrieval")
            seen.add(record.external_id)
        return self
