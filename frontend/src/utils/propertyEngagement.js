export function indexPropertyEngagement(items) {
  if (!Array.isArray(items)) return {}

  return Object.fromEntries(items.flatMap((item) => {
    const propertyId = Number(item?.property_id)
    if (!Number.isSafeInteger(propertyId) || propertyId < 1) return []
    return [[propertyId, {
      favorites: Math.max(0, Number(item.favorites) || 0),
      inquiries: Math.max(0, Number(item.inquiries) || 0),
      pending_inquiries: Math.max(0, Number(item.pending_inquiries) || 0),
    }]]
  }))
}
