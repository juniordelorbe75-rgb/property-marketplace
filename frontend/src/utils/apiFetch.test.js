import test from "node:test"
import assert from "node:assert/strict"

import {
  apiFetch,
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
