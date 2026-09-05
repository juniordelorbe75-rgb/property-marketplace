export function buildPropertyShareUrl(propertyId, currentUrl) {
  const id = Number(propertyId)
  if (!Number.isSafeInteger(id) || id < 1) throw new Error("Invalid property ID")
  const base = new URL(currentUrl)
  return new URL(`/properties/${id}`, base.origin).toString()
}

export async function shareProperty(property, capabilities, currentUrl) {
  const url = buildPropertyShareUrl(property?.id, currentUrl)
  const title = typeof property?.title === "string" && property.title
    ? property.title
    : "Anuncio de propiedad"
  const location = typeof property?.location === "string" ? property.location : ""
  const shareData = {
    title,
    text: location ? `View ${title} in ${location}.` : `View ${title}.`,
    url,
  }

  if (typeof capabilities?.share === "function") {
    try {
      await capabilities.share(shareData)
      return { method: "native", url }
    } catch (error) {
      if (error?.name === "AbortError") return { method: "cancelled", url }
    }
  }

  if (typeof capabilities?.clipboard?.writeText === "function") {
    try {
      await capabilities.clipboard.writeText(url)
      return { method: "clipboard", url }
    } catch {
      // A manual copy fallback remains available below.
    }
  }

  return { method: "manual", url }
}
