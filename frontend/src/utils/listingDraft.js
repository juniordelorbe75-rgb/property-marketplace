import { PROPERTY_AMENITIES } from "./propertyOptions.js"

const STORAGE_PREFIX = "property_marketplace_listing_draft_"
const PROPERTY_TYPES = new Set(["", "House", "Villa", "Apartment", "Condo"])
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

function storageFor(storage) {
  if (storage) return storage
  try { return globalThis.localStorage } catch { return null }
}

export function getDraftOwnerId(token) {
  if (typeof token !== "string") return ""
  try {
    const payload = token.split(".")[1]
    if (!payload) return ""
    const padded = payload.replace(/-/g, "+").replace(/_/g, "/").padEnd(
      Math.ceil(payload.length / 4) * 4,
      "=",
    )
    const subject = String(JSON.parse(globalThis.atob(padded)).sub || "")
    return /^\d+$/.test(subject) ? subject : ""
  } catch {
    return ""
  }
}

export function createListingKey() {
  return globalThis.crypto.randomUUID()
}

function cleanDraft(value) {
  if (!value || typeof value !== "object") return null
  const text = (name, maximum) => typeof value[name] === "string"
    ? value[name].slice(0, maximum)
    : ""
  return {
    title: text("title", 255),
    description: text("description", 2000),
    imageUrl: text("imageUrl", 2000),
    price: text("price", 30),
    currency: value.currency === "DOP" ? "DOP" : "USD",
    listingType: value.listingType === "rent" ? "rent" : "sale",
    amenities: Array.isArray(value.amenities)
      ? [...new Set(value.amenities.filter((item) => PROPERTY_AMENITIES.includes(item)))]
      : [],
    location: text("location", 255),
    province: text("province", 100),
    municipality: text("municipality", 100),
    sector: text("sector", 100),
    propertyType: PROPERTY_TYPES.has(value.propertyType) ? value.propertyType : "",
    bedrooms: text("bedrooms", 4),
    bathrooms: text("bathrooms", 4) || "1",
    squareFeet: text("squareFeet", 12),
    status: value.status === "unavailable" ? "unavailable" : "available",
    idempotencyKey: UUID_PATTERN.test(value.idempotencyKey || "")
      ? value.idempotencyKey
      : "",
  }
}

export function hasListingDraft(draft) {
  if (!draft) return false
  return Boolean(
    draft.title || draft.description || draft.imageUrl || draft.price
    || draft.location || draft.province || draft.municipality || draft.sector
    || draft.propertyType || draft.bedrooms
    || draft.squareFeet || draft.amenities.length,
  )
}

export function readListingDraft(ownerId, storage) {
  const target = storageFor(storage)
  if (!target || !/^\d+$/.test(String(ownerId))) return null
  try {
    return cleanDraft(JSON.parse(target.getItem(`${STORAGE_PREFIX}${ownerId}`) || "null"))
  } catch {
    return null
  }
}

export function saveListingDraft(ownerId, draft, storage) {
  const target = storageFor(storage)
  const cleaned = cleanDraft(draft)
  if (!target || !cleaned || !/^\d+$/.test(String(ownerId))) return
  try {
    const key = `${STORAGE_PREFIX}${ownerId}`
    if (hasListingDraft(cleaned)) target.setItem(key, JSON.stringify(cleaned))
    else target.removeItem(key)
  } catch {
    // Listing creation must remain usable when browser storage is unavailable.
  }
}

export function clearListingDraft(ownerId, storage) {
  const target = storageFor(storage)
  try { target?.removeItem(`${STORAGE_PREFIX}${ownerId}`) } catch {
    // Clearing a draft is best-effort when browser storage is unavailable.
  }
}
