export function getPropertyImageAlt(title, position) {
  const propertyTitle = String(title || "Propiedad").trim() || "Propiedad"
  return position ? `${propertyTitle} — imagen ${position}` : propertyTitle
}

export function getUnavailableImageLabel(title) {
  const propertyTitle = String(title || "Propiedad").trim() || "Propiedad"
  return `Imagen no disponible de ${propertyTitle}`
}
