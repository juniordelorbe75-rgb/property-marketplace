from fastapi import FastAPI
from backend.storage import load_properties, save_properties
from backend.models import Property

app = FastAPI()

properties = load_properties()


@app.get("/")
def home():
    return {"message": "Property Marketplace API is running"}


@app.get("/properties")
def get_properties():
    return properties


@app.get("/properties/{property_id}")
def get_property(property_id: int):
    for property in properties:
        if property["id"] == property_id:
            return property

    return {"message": "Property not found"}


@app.post("/properties")
def create_property(property: Property):
    properties.append(property.model_dump())
    save_properties(properties)
    return property

@app.put("/properties/{property_id}")
def update_property(property_id: int, updated_property: Property):
    for index, property in enumerate(properties):
        if property["id"] == property_id:
            properties[index] = updated_property.model_dump()
            save_properties(properties)
            return updated_property

    return {"message": "Property not found"}

@app.delete("/properties/{property_id}")
def delete_property(property_id: int):
    for index, property in enumerate(properties):
        if property["id"] == property_id:
            deleted_property = properties.pop(index)
            save_properties(properties)
            return deleted_property

    return {"message": "Property not found"}

