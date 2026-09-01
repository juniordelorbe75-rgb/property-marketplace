export function getPropertyImageAlt(title, position) {
  const propertyTitle = String(title || "Property").trim() || "Property"
  return position ? `${propertyTitle} — picture ${position}` : propertyTitle
}

export function getUnavailableImageLabel(title) {
  const propertyTitle = String(title || "Property").trim() || "Property"
  return `${propertyTitle} picture unavailable`
}
