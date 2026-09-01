const DEFAULT_TIMEOUT_MS = 20000
const MAX_READ_RETRIES = 2
const MAX_RETRY_DELAY_MS = 2000
const RETRYABLE_STATUSES = new Set([408, 429, 502, 503, 504])
import { AUTH_EXPIRED_EVENT, getExpiredSessionToken } from "./authSession.js"

export function isRetryableRequest(options = {}) {
  const method = (options.method || "GET").toUpperCase()
  return method === "GET" || method === "HEAD"
}

export function isRetryableStatus(status) {
  return RETRYABLE_STATUSES.has(status)
}

export function getRetryDelayMs(response, retryIndex) {
  const retryAfter = response?.headers?.get?.("retry-after")
  if (retryAfter) {
    const seconds = Number(retryAfter)
    if (Number.isFinite(seconds) && seconds >= 0) {
      return Math.min(seconds * 1000, MAX_RETRY_DELAY_MS)
    }

    const retryDate = Date.parse(retryAfter)
    if (Number.isFinite(retryDate)) {
      return Math.min(
        Math.max(0, retryDate - Date.now()),
        MAX_RETRY_DELAY_MS,
      )
    }
  }

  return Math.min(250 * (2 ** retryIndex), MAX_RETRY_DELAY_MS)
}

function waitForRetry(delayMs, signal) {
  return new Promise((resolve, reject) => {
    const timeout = window.setTimeout(finish, delayMs)

    function finish() {
      signal?.removeEventListener("abort", cancel)
      resolve()
    }

    function cancel() {
      window.clearTimeout(timeout)
      reject(signal.reason || new DOMException("Request cancelled", "AbortError"))
    }

    if (signal?.aborted) {
      cancel()
    } else {
      signal?.addEventListener("abort", cancel, { once: true })
    }
  })
}

export async function apiFetch(url, options = {}, timeoutMs = DEFAULT_TIMEOUT_MS) {
  const externalSignal = options.signal
  const canRetry = isRetryableRequest(options)

  for (let attempt = 0; ; attempt += 1) {
    const controller = new AbortController()
    let timedOut = false
    const handleExternalAbort = () => controller.abort(externalSignal.reason)

    if (externalSignal) {
      if (externalSignal.aborted) {
        handleExternalAbort()
      } else {
        externalSignal.addEventListener("abort", handleExternalAbort, { once: true })
      }
    }

    const timeout = window.setTimeout(() => {
      timedOut = true
      controller.abort()
    }, timeoutMs)

    try {
      const response = await fetch(url, { ...options, signal: controller.signal })
      const expiredToken = getExpiredSessionToken(response, options)

      if (expiredToken) {
        window.dispatchEvent(new CustomEvent(AUTH_EXPIRED_EVENT, {
          detail: { token: expiredToken },
        }))
      }

      if (
        canRetry
        && attempt < MAX_READ_RETRIES
        && isRetryableStatus(response.status)
      ) {
        await waitForRetry(getRetryDelayMs(response, attempt), externalSignal)
        continue
      }

      return response
    } catch (error) {
      if (timedOut) {
        throw new Error(
          "The request timed out. Please check the servers and try again.",
          { cause: error },
        )
      }
      if (
        canRetry
        && attempt < MAX_READ_RETRIES
        && !externalSignal?.aborted
      ) {
        await waitForRetry(250 * (2 ** attempt), externalSignal)
        continue
      }
      throw error
    } finally {
      window.clearTimeout(timeout)
      externalSignal?.removeEventListener("abort", handleExternalAbort)
    }
  }
}
