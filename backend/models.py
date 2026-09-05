import re
from datetime import date, datetime, timezone
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, Field, field_validator, model_validator

from backend.location_data import normalize_dominican_province, normalize_location_part


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


def normalize_name_part(value: str, label: str, required: bool = True) -> str:
    normalized = " ".join(value.strip().split())
    if required and len(normalized) < 1:
        raise ValueError(f"{label} is required")
    if len(normalized) > 100:
        raise ValueError(f"{label} must be at most 100 characters")
    return normalized


def validate_birth_date(value: date) -> date:
    today = datetime.now(timezone.utc).date()
    if value > today:
        raise ValueError("Date of birth cannot be in the future")
    if value.year < today.year - 120:
        raise ValueError("Enter a valid date of birth")
    return value


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


class ExternalProperty(BaseModel):
    id: int
    external_id: str
    source_url: str
    title: str
    description: str
    listing_type: str
    status: str
    price: float
    currency: str
    country_code: str
    province: str
    municipality: str
    sector: str
    property_type: str
    bedrooms: int | None
    bathrooms: float | None
    area_sqm: float | None
    image_urls: list[str]
    source_updated_at: datetime
    retrieved_at: datetime
    source_name: str
    attribution: str

    @classmethod
    def from_db(cls, item):
        return cls.model_validate({
            **{field: getattr(item, field) for field in cls.model_fields if field not in {"source_name", "attribution"}},
            "source_name": item.source.name,
            "attribution": item.source.attribution,
        })


class Property(BaseModel):
    id: int
    version: int
    owner_id: int
    owner_name: str
    owner_profile_public: bool = False
    title: str
    description: str
    image_url: str
    image_urls: list[str] = Field(default_factory=list)
    price: float
    currency: Literal["USD", "DOP"]
    listing_type: str
    amenities: list[str] = Field(default_factory=list)
    location: str
    country_code: Literal["DO"] = "DO"
    province: str = ""
    municipality: str = ""
    sector: str = ""
    property_type: str
    bedrooms: int
    bathrooms: int
    square_feet: int
    status: str
    safety_hold: bool = False
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
    country_code: Literal["DO"] = "DO"
    province: str = Field(default="", max_length=100)
    municipality: str = Field(default="", max_length=100)
    sector: str = Field(default="", max_length=100)
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

    @field_validator("province")
    @classmethod
    def validate_province(cls, value: str) -> str:
        return normalize_dominican_province(value)

    @field_validator("municipality", "sector")
    @classmethod
    def normalize_location_parts(cls, value: str) -> str:
        return normalize_location_part(value)

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
    country_code: Literal["DO"] = "DO"
    province: str = Field(default="", max_length=100)
    municipality: str = Field(default="", max_length=100)
    sector: str = Field(default="", max_length=100)
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

    @field_validator("province")
    @classmethod
    def validate_province(cls, value: str) -> str:
        return normalize_dominican_province(value)

    @field_validator("municipality", "sector")
    @classmethod
    def normalize_location_parts(cls, value: str) -> str:
        return normalize_location_part(value)

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
    name: str | None = Field(default=None, min_length=2, max_length=300)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str = Field(default="", max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    bio: str = Field(default="", max_length=1000)
    email: str = Field(min_length=3, max_length=255)
    password: str = Field(min_length=8, max_length=128)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return normalize_name(value) if value is not None else None

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_required_name_part(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        return normalize_name_part(value, info.field_name.replace("_", " ").title())

    @field_validator("middle_name")
    @classmethod
    def strip_middle_name(cls, value: str) -> str:
        return normalize_name_part(value, "Middle name", required=False)

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date | None) -> date | None:
        return validate_birth_date(value) if value else None

    @field_validator("bio")
    @classmethod
    def strip_bio(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def build_display_name(self):
        uses_structured_name = self.first_name is not None or self.last_name is not None
        if uses_structured_name:
            if not self.first_name or not self.last_name:
                raise ValueError("First name and last name are required")
            if self.date_of_birth is None:
                raise ValueError("Date of birth is required")
            self.name = " ".join(part for part in (self.first_name, self.middle_name, self.last_name) if part)
        elif not self.name:
            raise ValueError("First name and last name are required")
        return self

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


class PasswordResetRequest(BaseModel):
    email: str = Field(min_length=3, max_length=255)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class PasswordResetConfirmation(BaseModel):
    token: str = Field(min_length=32, max_length=256)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_new_password(value)


class EmailVerificationConfirmation(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class UserResponse(BaseModel):
    id: int
    name: str
    email: str
    first_name: str = ""
    middle_name: str = ""
    last_name: str = ""
    date_of_birth: date | None = None
    bio: str = ""
    public_profile_enabled: bool = False
    public_name_mode: Literal["first_name", "full_name"] = "first_name"
    public_bio_visible: bool = False
    has_password: bool = True
    email_verified: bool = False

    model_config = {
        "from_attributes": True
    }


class UserUpdateResponse(UserResponse):
    access_token: str | None = None
    token_type: str | None = None


class UserUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=300)
    first_name: str | None = Field(default=None, max_length=100)
    middle_name: str = Field(default="", max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    date_of_birth: date | None = None
    bio: str = Field(default="", max_length=1000)
    public_profile_enabled: bool = False
    public_name_mode: Literal["first_name", "full_name"] = "first_name"
    public_bio_visible: bool = False
    email: str = Field(min_length=3, max_length=255)
    current_password: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return normalize_name(value) if value is not None else None

    @field_validator("first_name", "last_name")
    @classmethod
    def strip_required_name_part(cls, value: str | None, info) -> str | None:
        if value is None:
            return None
        return normalize_name_part(value, info.field_name.replace("_", " ").title())

    @field_validator("middle_name")
    @classmethod
    def strip_middle_name(cls, value: str) -> str:
        return normalize_name_part(value, "Middle name", required=False)

    @field_validator("date_of_birth")
    @classmethod
    def validate_date_of_birth(cls, value: date | None) -> date | None:
        return validate_birth_date(value) if value else None

    @field_validator("bio")
    @classmethod
    def strip_bio(cls, value: str) -> str:
        return value.strip()

    @model_validator(mode="after")
    def build_display_name(self):
        uses_structured_name = self.first_name is not None or self.last_name is not None
        if uses_structured_name:
            if not self.first_name or not self.last_name:
                raise ValueError("First name and last name are required")
            if self.date_of_birth is None:
                raise ValueError("Date of birth is required")
            self.name = " ".join(part for part in (self.first_name, self.middle_name, self.last_name) if part)
        elif not self.name:
            raise ValueError("First name and last name are required")
        return self

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        return normalize_email(value)


class PasswordChange(BaseModel):
    current_password: str | None = Field(default=None, min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, value: str) -> str:
        return validate_new_password(value)


class PublicProfile(BaseModel):
    id: int
    display_name: str
    bio: str | None = None


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


class ListingReport(BaseModel):
    id: int
    listing_id: int
    listing_title: str
    reason: str
    details: str
    status: str
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class MyListingReport(ListingReport):
    property_id: int | None
    updated_at: datetime


class MyListingReportPage(BaseModel):
    items: list[MyListingReport]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminListingReport(ListingReport):
    property_id: int | None
    listing_owner_id: int
    listing_owner_name: str
    reporter_id: int
    reporter_name: str
    moderator_note: str
    reviewed_at: datetime | None
    reviewer_name: str | None
    updated_at: datetime
    version: int
    listing_on_safety_hold: bool | None
    listing_safety_version: int | None


class ListingReportStatusCounts(BaseModel):
    all: int
    submitted: int
    reviewing: int
    resolved: int
    dismissed: int


class ListingReportPage(BaseModel):
    items: list[AdminListingReport]
    total: int
    page: int
    page_size: int
    total_pages: int
    counts: ListingReportStatusCounts


class AdminAccess(BaseModel):
    is_admin: bool


class ListingSafetyHold(BaseModel):
    listing_id: int
    safety_hold: bool
    safety_version: int
    safety_updated_at: datetime | None


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
