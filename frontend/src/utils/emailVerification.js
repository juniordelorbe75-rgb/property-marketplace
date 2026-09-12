import { apiFetch } from "./apiFetch.js"
import { getApiError } from "./apiError.js"
import { readApiResponse } from "./apiResponse.js"

// Keep a single request and its result for this mounted verification page.
// Replayed effects must subscribe to it, rather than consume the link again.
export function createEmailVerifier(request = apiFetch) {
  let currentRequest
  return (token) => {
    if (currentRequest?.token === token) return currentRequest.promise
    const promise = (async () => {
      const response = await request("/users/email-verification/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "No pudimos verificar su correo electrónico"))
      return data
    })()
    currentRequest = { token, promise }
    return promise
  }
}
