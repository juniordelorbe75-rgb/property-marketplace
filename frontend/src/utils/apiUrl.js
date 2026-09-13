const configuredApiBaseUrl = (import.meta.env?.VITE_API_BASE_URL || "")
  .trim()
  .replace(/\/+$/, "")


export function resolveApiUrl(url, apiBaseUrl = configuredApiBaseUrl) {
  const normalizedBaseUrl = apiBaseUrl.trim().replace(/\/+$/, "")
  if (!normalizedBaseUrl || typeof url !== "string" || !url.startsWith("/")) {
    return url
  }
  return `${normalizedBaseUrl}${url}`
}
