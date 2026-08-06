from pydantic import BaseModel, field_validator


class Property(BaseModel):
    id: int
    title: str
    price: float
    location: str

    @field_validator("location")
    @classmethod
    def normalize_location(cls, value):
        return value.title()