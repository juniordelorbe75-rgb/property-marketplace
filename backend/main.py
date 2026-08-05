from fastapi import FastAPI
from backend.data import properties
from backend.models import Property

app = FastAPI()


@app.get("/")
def home():
    return {"message": "Property Marketplace API is running"}


@app.get("/properties")
def get_properties():
    return properties


@app.get("/properties/{property_id}")
def get_property(property_id: int):
    for property in properties:
        if property.id == property_id:
            return property

    return {"message": "Property not found"}


@app.post("/properties")
def create_property(property: Property):
    properties.append(property)
    return property