import re
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator


EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
BCRYPT_MAX_PASSWORD_BYTES = 72
Amenity = Literal[
    "Garage",
    "Pool",
    "Yard",
    "Balcony",
    "Gym",
    "Air Conditioning",
    "Furnished",
    "Pet Friendly",
]


def normalize_email(value: str) -> str:
    normalized = value.strip().lower()

    if not EMAIL_PATTERN.fullmatch(normalized):
        raise ValueError("Enter a valid email address")

    return normalized


def normalize_name(value: str) -> str:
    normalized = value.strip()

    if len(normalized) < 2:
        raise ValueError("Name must be at least 2 characters")

    return normalized


def validate_new_password(value: str) -> str:
    if len(value.encode("utf-8")) > BCRYPT_MAX_PASSWORD_BYTES:
        raise ValueError("Password must be at most 72 UTF-8 bytes")
    return value


def normalize_property_text(
    value: str,
    field_name: str,
    minimum_length: int,
) -> str:
    normalized = value.strip()

    if len(normalized) < minimum_length:
        raise ValueError(
            f"{field_name} must be at least {minimum_length} characters"
        )

    return normalized


def normalize_image_url(value: str) -> str:
    normalized = value.strip()

    if not normalized:
        return ""

    if normalized.startswith("/uploads/property-images/"):
        return normalized

    parsed = urlsplit(normalized)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("Image URL must be a valid HTTP or HTTPS URL")

    return normalized


class PropertyImageUpload(BaseModel):
    filename: str = Field(min_length=1, max_length=255)
    content_type: Literal["image/jpeg", "image/png", "image/webp"]
    data: str = Field(min_length=1, max_length=8_000_000)


class PropertyImageUploadResponse(BaseModel):
    image_url: str


class SellerDashboardStats(BaseModel):
    total_listings: int
    available_listings: int
    unavailable_listings: int
    favorites_received: int
    inquiries_received: int
    pending_inquiries: int


class PropertyEngagement(BaseModel):
    property_id: int
    favorites: int
    inquiries: int
    pending_inquiries: int


class Property(BaseModel):
    id: int
    version: int
    owner_id: int
    owner_name: str
    title: str
    description: str
    image_url: str
    image_urls: list[str] = Field(default_factory=list)
    price: float
    currency: Literal["USD", "DOP"]
    listing_type: str
    amenities: list[str] = Field(default_factory=list)
    location: str
    property_type: str
    bedrooms: int
    bathrooms: int
    square_feet: int
    status: str
    created_at: datetime
    updated_at: datetime

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value):
        return value.title()

    model_config = {
        "from_attributes": True
    }


class PropertyCreate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=2000)
    image_url: str = Field(default="", max_length=2000)
    image_urls: list[str] = Field(default_factory=list, max_length=8)
    price: float = Field(gt=0)
    currency: Literal["USD", "DOP"] = "USD"
    listing_type: Literal["sale", "rent"] = "sale"
    amenities: list[Amenity] = Field(default_factory=list, max_length=8)
    location: str = Field(min_length=2, max_length=255)
    property_type: Literal["House", "Villa", "Apartment", "Condo"]
    bedrooms: int = Field(ge=0, le=100)
    bathrooms: int = Field(default=1, ge=0, le=100)
    square_feet: int = Field(default=0, ge=0, le=10000000)
    status: Literal["available", "unavailable"] = "available"

    @field_validator("title", "location", "description")
    @classmethod
    def strip_text(cls, value: str, info) -> str:
        if info.field_name == "description":
            return value.strip()

        minimum_length = 3 if info.field_name == "title" else 2
        return normalize_property_text(
            value,
            info.field_name.replace("_", " ").title(),
            minimum_length,
        )

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str) -> str:
        return normalize_image_url(value)

    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(normalize_image_url(value) for value in values if value))

    @model_validator(mode="after")
    def synchronize_images(self):
        images = self.image_urls or ([self.image_url] if self.image_url else [])
        if not images:
            raise ValueError("At least one property picture is required")
        self.image_urls = images
        self.image_url = images[0] if images else ""
        return self


class PropertyUpdate(BaseModel):
    title: str = Field(min_length=3, max_length=255)
    description: str = Field(default="", max_length=2000)
    image_url: str = Field(default="", max_length=2000)
    image_urls: list[str] = Field(default_factory=list, max_length=8)
    price: float = Field(gt=0)
    currency: Literal["USD", "DOP"]
    listing_type: Literal["sale", "rent"] = "sale"
    amenities: list[Amenity] = Field(default_factory=list, max_length=8)
    location: str = Field(min_length=2, max_length=255)
    property_type: Literal["House", "Villa", "Apartment", "Condo"]
    bedrooms: int = Field(ge=0, le=100)
    bathrooms: int = Field(default=1, ge=0, le=100)
    square_feet: int = Field(default=0, ge=0, le=10000000)
    status: Literal["available", "unavailable"]

    @field_validator("title", "location", "description")
    @classmethod
    def strip_text(cls, value: str, info) -> str:
        if info.field_name == "description":
            return value.strip()

        minimum_length = 3 if info.field_name == "title" else 2
        return normalize_property_text(
            value,
            info.field_name.replace("_", " ").title(),
            minimum_length,
        )

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str) -> str:
        return normalize_image_url(value)

    @field_validator("image_urls")
    @classmethod
    def validate_image_urls(cls, values: list[str]) -> list[str]:
        return list(dict.fromkeys(normalize_image_url(value) for value in values if value))

    @model_validator(mode="after")
    def synchronize_images(self):
        images = self.image_urls or ([self.image_url] if self.image_url else [])
        if not images:
            raise ValueError("At least one property picture is required")
        self.image_urls = images
        self.image_url = images[0] if images else ""
        return self


class User(BaseModel):
    id: int
    name: str
    email: str
    password: str
    role: str = "buyer"


class UserCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return normalize_name(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)

    @field_validator("password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_new_password(value)


class UserLogin(BaseModel):
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str

    model_config = {
        "from_attributes": True
    }


class UserUpdate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(min_length=3, max_length=255)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return normalize_name(value)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_new_password(value)


class AccountDeletionConfirmation(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)


class Favorite(BaseModel):
    id: int
    user_id: int
    property_id: int

    model_config = {
        "from_attributes": True
    }


class FavoritePropertyResponse(BaseModel):
    id: int
    property: Property

    model_config = {
        "from_attributes": True
    }


class FavoriteStatus(BaseModel):
    is_favorite: bool


class InquiryMessage(BaseModel):
    id: int | None = None
    sender_id: int
    sender_role: str
    sender_name: str
    body: str
    created_at: datetime


class Inquiry(BaseModel):
    id: int
    property_id: int
    buyer_id: int
    seller_id: int
    message: str
    reply: str | None = None
    status: str = "pending"
    created_at: datetime
    updated_at: datetime
    property_title: str
    buyer_name: str
    seller_name: str
    conversation_messages: list[InquiryMessage] = Field(default_factory=list)
    unread_count: int = 0
    read_through_at: datetime

    model_config = {
        "from_attributes": True
    }


class InquiryStatusCounts(BaseModel):
    all: int
    pending: int
    accepted: int
    rejected: int
    cancelled: int


class InquiryPage(BaseModel):
    items: list[Inquiry]
    total: int
    page: int
    page_size: int
    total_pages: int
    counts: InquiryStatusCounts


class InquiryUnreadCount(BaseModel):
    unread_count: int
