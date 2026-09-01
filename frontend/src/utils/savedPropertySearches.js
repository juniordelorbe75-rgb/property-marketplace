import {
  buildPropertySearchParams,
  readPropertySearchParams,
} from "./propertySearchParams.js"

const STORAGE_KEY = "property_marketplace_saved_searches"
const MAX_SAVED_SEARCHES = 6

function canonicalQuery(input) {
  const parsed = readPropertySearchParams(input)
  return buildPropertySearchParams(parsed).toString()
}

export function describePropertySearch(input) {
  const search = readPropertySearchParams(input)
  const parts = []

  if (search.reference) parts.push(search.reference)
  if (search.location) parts.push(search.location)
  if (search.listingType) parts.push(search.listingType === "rent" ? "For Rent" : "For Sale")
  if (search.propertyType) parts.push(search.propertyType)
  if (search.currency) parts.push(search.currency === "DOP" ? "Dominican Pesos" : "US Dollars")
  const pricePrefix = search.currency === "DOP" ? "RD$" : "US$"
  if (search.minPrice) parts.push(`From ${pricePrefix}${Number(search.minPrice).toLocaleString()}`)
  if (search.maxPrice) parts.push(`Up to ${pricePrefix}${Number(search.maxPrice).toLocaleString()}`)
  if (search.bedrooms) parts.push(`${search.bedrooms}+ beds`)
  if (search.bathrooms) parts.push(`${search.bathrooms}+ baths`)
  if (search.amenity) parts.push(search.amenity)
  if (search.minSquareFeet) parts.push(`${Number(search.minSquareFeet).toLocaleString()}+ sq ft`)
  if (search.status) parts.push(search.status === "available" ? "Available" : "Unavailable")

  return parts.join(" · ") || "All properties"
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
