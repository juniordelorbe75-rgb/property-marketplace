import { formatPropertyReference } from "./propertyReference.js"

export const SELLER_LISTING_FILTERS = ["all", "available", "unavailable", "attention"]

export function filterSellerListings(properties, engagementByProperty, query, statusFilter) {
  const normalizedQuery = String(query || "").trim().toLocaleLowerCase()
  const safeFilter = SELLER_LISTING_FILTERS.includes(statusFilter) ? statusFilter : "all"

  return properties.filter((property) => {
    const engagement = engagementByProperty[property.id] || {}
    const matchesStatus = safeFilter === "all"
      || property.status === safeFilter
      || (safeFilter === "attention" && Number(engagement.pending_inquiries) > 0)

    if (!matchesStatus) return false
    if (!normalizedQuery) return true

    return [property.title, property.location, formatPropertyReference(property.id)]
      .some((value) => String(value || "").toLocaleLowerCase().includes(normalizedQuery))
  })
}

export function countSellerListingFilters(properties, engagementByProperty) {
  return {
    all: properties.length,
    available: properties.filter((property) => property.status === "available").length,
    unavailable: properties.filter((property) => property.status === "unavailable").length,
    attention: properties.filter(
      (property) => Number(engagementByProperty[property.id]?.pending_inquiries) > 0,
    ).length,
  }
}
