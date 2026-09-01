import { PROPERTY_AMENITIES } from "./propertyOptions.js"
import { normalizePropertyReference } from "./propertyReference.js"

const PROPERTY_TYPES = new Set(["House", "Villa", "Apartment", "Condo"])
const LISTING_TYPES = new Set(["sale", "rent"])
const STATUSES = new Set(["available", "unavailable"])
const SORT_OPTIONS = new Set(["newest", "price_low", "price_high"])
const CURRENCIES = new Set(["USD", "DOP"])

function enumValue(params, name, allowed) {
  const value = params.get(name) || ""
  return allowed.has(value) ? value : ""
}

function numberValue(params, name, maximum = Number.MAX_SAFE_INTEGER) {
  const value = params.get(name) || ""
  if (!/^\d+(\.\d+)?$/.test(value)) return ""
  const number = Number(value)
  return Number.isFinite(number) && number >= 0 && number <= maximum ? value : ""
}

export function readPropertySearchParams(input) {
  const params = input instanceof URLSearchParams ? input : new URLSearchParams(input)
  const rawPage = params.get("page") || "1"
  const page = /^\d+$/.test(rawPage) && Number(rawPage) >= 1 ? Number(rawPage) : 1
  const currency = enumValue(params, "currency", CURRENCIES)
  const requestedSort = enumValue(params, "sort_by", SORT_OPTIONS) || "newest"

  return {
    reference: normalizePropertyReference(params.get("reference")),
    location: (params.get("location") || "").trim().slice(0, 200),
    minPrice: currency ? numberValue(params, "min_price") : "",
    maxPrice: currency ? numberValue(params, "max_price") : "",
    currency,
    propertyType: enumValue(params, "property_type", PROPERTY_TYPES),
    listingType: enumValue(params, "listing_type", LISTING_TYPES),
    amenity: enumValue(params, "amenity", new Set(PROPERTY_AMENITIES)),
    bedrooms: numberValue(params, "bedrooms", 100),
    bathrooms: numberValue(params, "bathrooms", 100),
    minSquareFeet: numberValue(params, "min_square_feet", 10000000),
    status: enumValue(params, "status", STATUSES),
    sortBy: requestedSort.startsWith("price_") && !currency ? "newest" : requestedSort,
    page,
  }
}

export function buildPropertySearchParams(search, page = 1) {
  const params = new URLSearchParams()
  const mappings = [
    ["reference", normalizePropertyReference(search.reference)],
    ["location", search.location?.trim()],
    ["min_price", search.minPrice],
    ["max_price", search.maxPrice],
    ["currency", search.currency],
    ["property_type", search.propertyType],
    ["listing_type", search.listingType],
    ["amenity", search.amenity],
    ["bedrooms", search.bedrooms],
    ["bathrooms", search.bathrooms],
    ["min_square_feet", search.minSquareFeet],
    ["status", search.status],
  ]

  mappings.forEach(([name, value]) => {
    if (value !== "" && value != null) params.set(name, String(value))
  })
  if (search.sortBy && search.sortBy !== "newest") params.set("sort_by", search.sortBy)
  if (page > 1) params.set("page", String(page))
  return params
}

export function getPropertyApiSearchParams(params) {
  const parsed = readPropertySearchParams(params)
  const apiParams = buildPropertySearchParams(parsed)
  apiParams.delete("page")
  return apiParams
}
