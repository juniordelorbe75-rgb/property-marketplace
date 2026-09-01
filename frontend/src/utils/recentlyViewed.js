const STORAGE_KEY = "property_marketplace_recently_viewed"
const MAX_RECENT_PROPERTIES = 6

function getStorage(storage) {
  if (storage) return storage
  try {
    return globalThis.localStorage
  } catch {
    return null
  }
}

function propertySnapshot(property) {
  const id = Number(property?.id)
  if (!Number.isSafeInteger(id) || id < 1) return null

  const requiredText = ["title", "location", "property_type", "status"]
  if (requiredText.some((field) => typeof property[field] !== "string")) return null

  const price = Number(property.price)
  const bedrooms = Number(property.bedrooms)
  const bathrooms = Number(property.bathrooms)
  const squareFeet = Number(property.square_feet || 0)
  const ownerId = Number(property.owner_id)
  if (![price, bedrooms, bathrooms, squareFeet].every(Number.isFinite)) return null

  return {
    id,
    owner_id: Number.isSafeInteger(ownerId) && ownerId > 0 ? ownerId : null,
    title: property.title.slice(0, 255),
    location: property.location.slice(0, 255),
    property_type: property.property_type.slice(0, 100),
    status: property.status,
    listing_type: property.listing_type === "rent" ? "rent" : "sale",
    image_url: typeof property.image_url === "string" ? property.image_url.slice(0, 2000) : "",
    price,
    currency: property.currency === "DOP" ? "DOP" : "USD",
    bedrooms,
    bathrooms,
    square_feet: squareFeet,
  }
}

export function readRecentlyViewed(storage) {
  const target = getStorage(storage)
  if (!target) return []

  try {
    const value = JSON.parse(target.getItem(STORAGE_KEY) || "[]")
    if (!Array.isArray(value)) return []
    return value.map(propertySnapshot).filter(Boolean).slice(0, MAX_RECENT_PROPERTIES)
  } catch {
    return []
  }
}

export function rememberRecentlyViewed(property, storage) {
  const target = getStorage(storage)
  const snapshot = propertySnapshot(property)
  if (!target || !snapshot) return readRecentlyViewed(storage)

  const recent = [
    snapshot,
    ...readRecentlyViewed(target).filter((item) => item.id !== snapshot.id),
  ].slice(0, MAX_RECENT_PROPERTIES)

  try {
    target.setItem(STORAGE_KEY, JSON.stringify(recent))
  } catch {
    // Browsing must continue when storage is blocked or full.
  }
  return recent
}

export function clearRecentlyViewed(storage) {
  const target = getStorage(storage)
  try {
    target?.removeItem(STORAGE_KEY)
  } catch {
    // Clearing history is best-effort when browser storage is unavailable.
  }
}
