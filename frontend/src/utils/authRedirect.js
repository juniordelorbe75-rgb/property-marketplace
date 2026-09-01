const FALLBACK_PATH = "/"

export function getReturnPath(location) {
  if (!location) return FALLBACK_PATH

  const path = `${location.pathname || ""}${location.search || ""}${location.hash || ""}`
  return path.startsWith("/") && !path.startsWith("//") ? path : FALLBACK_PATH
}

export function getSafeReturnPath(value) {
  if (typeof value !== "string") return FALLBACK_PATH
  if (!value.startsWith("/") || value.startsWith("//")) return FALLBACK_PATH

  try {
    const parsed = new URL(value, "http://marketplace.local")
    if (parsed.origin !== "http://marketplace.local") return FALLBACK_PATH
    return `${parsed.pathname}${parsed.search}${parsed.hash}`
  } catch {
    return FALLBACK_PATH
  }
}
