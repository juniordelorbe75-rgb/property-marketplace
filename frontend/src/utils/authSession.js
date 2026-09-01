export const AUTH_EXPIRED_EVENT = "marketplace:auth-expired"

export function getRequestBearerToken(options = {}) {
  const headers = new Headers(options.headers || {})
  const authorization = headers.get("authorization") || ""
  const match = authorization.match(/^Bearer\s+(.+)$/i)
  return match?.[1]?.trim() || ""
}

export function getExpiredSessionToken(response, options = {}) {
  if (response.status !== 401) return ""
  return getRequestBearerToken(options)
}
