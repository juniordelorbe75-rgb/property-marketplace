const SQUARE_FEET_PER_SQUARE_METER = 10.763910416709722

export function getExternalCatalogApiSearchParams(search, page = 1, pageSize = 9) {
  if (search.reference || search.status === "unavailable") return null

  const params = new URLSearchParams()
  const mappings = [
    ["location", search.location],
    ["min_price", search.minPrice],
    ["max_price", search.maxPrice],
    ["currency", search.currency],
    ["property_type", search.propertyType],
    ["listing_type", search.listingType],
    ["amenity", search.amenity],
    ["bedrooms", search.bedrooms],
    ["bathrooms", search.bathrooms],
  ]

  for (const [name, value] of mappings) {
    if (value !== "" && value != null) params.set(name, String(value))
  }

  if (search.minSquareFeet !== "" && search.minSquareFeet != null) {
    const squareFeet = Number(search.minSquareFeet)
    if (Number.isFinite(squareFeet) && squareFeet >= 0) {
      params.set("min_area_sqm", String(squareFeet / SQUARE_FEET_PER_SQUARE_METER))
    }
  }

  if (search.sortBy && search.sortBy !== "newest") {
    params.set("sort_by", search.sortBy)
  }

  params.set("limit", String(pageSize))
  params.set("offset", String(Math.max(0, page - 1) * pageSize))
  return params
}

export function getCombinedResultPageCount(nativeTotal, externalTotal, pageSize = 9) {
  const nativePages = Math.ceil(Math.max(0, nativeTotal) / pageSize)
  const externalPages = Math.ceil(Math.max(0, externalTotal) / pageSize)
  return Math.max(1, nativePages, externalPages)
}
