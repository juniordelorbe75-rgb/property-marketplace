export function buildPropertyMapUrl(location) {
  const query = String(location || "").trim().slice(0, 255)
  if (!query) return ""

  const url = new URL("https://www.google.com/maps/search/")
  url.searchParams.set("api", "1")
  url.searchParams.set("query", query)
  return url.toString()
}

export function isMapLocationDetailed(location) {
  const parts = String(location || "")
    .split(",")
    .map((part) => part.trim())
    .filter(Boolean)

  return parts.length >= 2
}
