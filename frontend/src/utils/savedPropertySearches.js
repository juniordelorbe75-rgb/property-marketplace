import {
  buildPropertySearchParams,
  readPropertySearchParams,
} from "./propertySearchParams.js"

const STORAGE_KEY = "property_marketplace_saved_searches"
const MAX_SAVED_SEARCHES = 6
const PROPERTY_TYPE_LABELS = { House: "Casa", Villa: "Villa", Apartment: "Apartamento", Condo: "Condominio" }
const AMENITY_LABELS = {
  Garage: "Garaje", Pool: "Piscina", Yard: "Patio", Balcony: "Balcón",
  Gym: "Gimnasio", "Air Conditioning": "Aire acondicionado",
  Furnished: "Amueblada", "Pet Friendly": "Acepta mascotas",
}

function canonicalQuery(input) {
  const parsed = readPropertySearchParams(input)
  return buildPropertySearchParams(parsed).toString()
}

export function describePropertySearch(input) {
  const search = readPropertySearchParams(input)
  const parts = []

  if (search.reference) parts.push(search.reference)
  if (search.location) parts.push(search.location)
  if (search.listingType) parts.push(search.listingType === "rent" ? "En alquiler" : "En venta")
  if (search.propertyType) parts.push(PROPERTY_TYPE_LABELS[search.propertyType] || search.propertyType)
  if (search.currency) parts.push(search.currency === "DOP" ? "Pesos dominicanos" : "Dólares estadounidenses")
  const pricePrefix = search.currency === "DOP" ? "RD$" : "US$"
  if (search.minPrice) parts.push(`Desde ${pricePrefix}${Number(search.minPrice).toLocaleString("es-DO")}`)
  if (search.maxPrice) parts.push(`Hasta ${pricePrefix}${Number(search.maxPrice).toLocaleString("es-DO")}`)
  if (search.bedrooms) parts.push(`${search.bedrooms}+ habitaciones`)
  if (search.bathrooms) parts.push(`${search.bathrooms}+ baños`)
  if (search.amenity) parts.push(AMENITY_LABELS[search.amenity] || search.amenity)
  if (search.minSquareFeet) parts.push(`${Number(search.minSquareFeet).toLocaleString("es-DO")}+ pies²`)
  if (search.status) parts.push(search.status === "available" ? "Disponible" : "No disponible")

  return parts.join(" · ") || "Todas las propiedades"
}

export function readSavedPropertySearches(storage = localStorage) {
  try {
    const stored = JSON.parse(storage.getItem(STORAGE_KEY) || "[]")
    if (!Array.isArray(stored)) return []

    return stored.flatMap((item) => {
      if (!item || typeof item.query !== "string") return []
      const query = canonicalQuery(item.query)
      if (!query) return []
      return [{ query, label: describePropertySearch(query) }]
    }).slice(0, MAX_SAVED_SEARCHES)
  } catch {
    return []
  }
}

export function savePropertySearch(storage, input) {
  const query = canonicalQuery(input)
  const current = readSavedPropertySearches(storage)
  if (!query) return current

  const next = [
    { query, label: describePropertySearch(query) },
    ...current.filter((item) => item.query !== query),
  ].slice(0, MAX_SAVED_SEARCHES)

  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    return current
  }
  return next
}

export function removeSavedPropertySearch(storage, query) {
  const next = readSavedPropertySearches(storage).filter((item) => item.query !== query)
  try {
    storage.setItem(STORAGE_KEY, JSON.stringify(next))
  } catch {
    return readSavedPropertySearches(storage)
  }
  return next
}
