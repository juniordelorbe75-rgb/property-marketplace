export const PROPERTY_AMENITIES = [
  "Garage",
  "Pool",
  "Yard",
  "Balcony",
  "Gym",
  "Air Conditioning",
  "Furnished",
  "Pet Friendly",
]

const PROPERTY_AMENITY_LABELS = {
  Garage: "Garaje",
  Pool: "Piscina",
  Yard: "Patio",
  Balcony: "Balcón",
  Gym: "Gimnasio",
  "Air Conditioning": "Aire acondicionado",
  Furnished: "Amueblada",
  "Pet Friendly": "Acepta mascotas",
}

export function getPropertyAmenityLabel(value) {
  return PROPERTY_AMENITY_LABELS[value] || value
}
