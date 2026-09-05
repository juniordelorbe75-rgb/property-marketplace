import test from "node:test"
import assert from "node:assert/strict"

import {
  apiFetch,
  getRequestFailureMessage,
  getRetryDelayMs,
  isRetryableRequest,
  isRetryableStatus,
} from "./apiFetch.js"


test("retries only safe read methods", () => {
  assert.equal(isRetryableRequest(), true)
  assert.equal(isRetryableRequest({ method: "get" }), true)
  assert.equal(isRetryableRequest({ method: "HEAD" }), true)
  assert.equal(isRetryableRequest({ method: "POST" }), false)
  assert.equal(isRetryableRequest({ method: "PUT" }), false)
  assert.equal(isRetryableRequest({ method: "PATCH" }), false)
  assert.equal(isRetryableRequest({ method: "DELETE" }), false)
})

test("retries only temporary response statuses", () => {
  for (const status of [408, 429, 502, 503, 504]) {
    assert.equal(isRetryableStatus(status), true)
  }
  for (const status of [400, 401, 403, 404, 409, 500]) {
    assert.equal(isRetryableStatus(status), false)
  }
})

test("uses bounded retry-after and exponential fallback delays", () => {
  const secondsResponse = {
    headers: { get: () => "10" },
  }
  const noHeaderResponse = {
    headers: { get: () => null },
  }

  assert.equal(getRetryDelayMs(secondsResponse, 0), 2000)
  assert.equal(getRetryDelayMs(noHeaderResponse, 0), 250)
  assert.equal(getRetryDelayMs(noHeaderResponse, 1), 500)
})

test("retries temporary reads but never replays writes", async () => {
  const originalWindow = globalThis.window
  const originalFetch = globalThis.fetch
  globalThis.window = {
    setTimeout,
    clearTimeout,
    dispatchEvent() {},
  }

  try {
    let readCalls = 0
    globalThis.fetch = async () => {
      readCalls += 1
      return {
        status: readCalls < 3 ? 503 : 200,
        headers: { get: () => "0" },
      }
    }

    const readResponse = await apiFetch("/properties/")
    assert.equal(readResponse.status, 200)
    assert.equal(readCalls, 3)

    let writeCalls = 0
    globalThis.fetch = async () => {
      writeCalls += 1
      return { status: 503, headers: { get: () => "0" } }
    }

    const writeResponse = await apiFetch("/inquiries/", { method: "POST" })
    assert.equal(writeResponse.status, 503)
    assert.equal(writeCalls, 1)
  } finally {
    globalThis.window = originalWindow
    globalThis.fetch = originalFetch
  }
})

test("explains offline, read, and unconfirmed write failures differently", () => {
  assert.match(getRequestFailureMessage({ isOnline: false }), /no tiene conexión/i)
  assert.match(getRequestFailureMessage(), /no pudimos comunicarnos/i)
  assert.match(
    getRequestFailureMessage({ isWrite: true }),
    /antes de confirmar.*información más reciente/i,
  )
  assert.match(
    getRequestFailureMessage({ isWrite: true, timedOut: true }),
    /agotó el tiempo antes de confirmarse/i,
  )
})

test("does not send a request while the browser reports offline", async () => {
  const originalNavigator = Object.getOwnPropertyDescriptor(globalThis, "navigator")
  const originalFetch = globalThis.fetch
  let fetchCalls = 0
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: { onLine: false },
  })
  globalThis.fetch = async () => {
    fetchCalls += 1
  }

  try {
    await assert.rejects(apiFetch("/properties/"), /no tiene conexión/i)
    assert.equal(fetchCalls, 0)
  } finally {
    globalThis.fetch = originalFetch
    if (originalNavigator) {
      Object.defineProperty(globalThis, "navigator", originalNavigator)
    } else {
      delete globalThis.navigator
    }
  }
})

test("preserves navigation cancellation even when the browser is offline", async () => {
  const originalNavigator = Object.getOwnPropertyDescriptor(globalThis, "navigator")
  Object.defineProperty(globalThis, "navigator", {
    configurable: true,
    value: { onLine: false },
  })
  const controller = new AbortController()
  controller.abort()

  try {
    await assert.rejects(
      apiFetch("/properties/", { signal: controller.signal }),
      { name: "AbortError" },
    )
  } finally {
    if (originalNavigator) {
      Object.defineProperty(globalThis, "navigator", originalNavigator)
    } else {
      delete globalThis.navigator
    }
  }
})

test("does not replay an interrupted write and warns about missing confirmation", async () => {
  const originalWindow = globalThis.window
  const originalFetch = globalThis.fetch
  globalThis.window = { setTimeout, clearTimeout }
  let fetchCalls = 0
  globalThis.fetch = async () => {
    fetchCalls += 1
    throw new TypeError("Failed to fetch")
  }

  try {
    await assert.rejects(
      apiFetch("/inquiries/1/messages", { method: "POST" }),
      /antes de confirmar.*información más reciente/i,
    )
    assert.equal(fetchCalls, 1)
  } finally {
    globalThis.window = originalWindow
    globalThis.fetch = originalFetch
  }
})
