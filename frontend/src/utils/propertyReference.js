export function formatPropertyReference(propertyId) {
  const id = Number(propertyId)
  if (!Number.isSafeInteger(id) || id < 1) return ""
  return `PM-${String(id).padStart(6, "0")}`
}

export function normalizePropertyReference(value) {
  const normalized = String(value || "").trim().toUpperCase()
  const digits = /^\d+$/.test(normalized)
    ? normalized
    : normalized.match(/^PM-(\d+)$/)?.[1]
  if (!digits) return ""

  const id = Number(digits)
  return formatPropertyReference(id)
}

export function propertyIdFromReference(value) {
  const reference = normalizePropertyReference(value)
  if (!reference) return null
  return Number(reference.slice(3))
}
