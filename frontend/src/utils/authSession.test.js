import test from "node:test"
import assert from "node:assert/strict"

import { getExpiredSessionToken, getRequestBearerToken } from "./authSession.js"

test("extracts bearer tokens regardless of header casing", () => {
  assert.equal(
    getRequestBearerToken({ headers: { Authorization: "Bearer current-token" } }),
    "current-token",
  )
})

test("expires only authenticated requests that receive 401", () => {
  const options = { headers: { authorization: "Bearer expired-token" } }

  assert.equal(getExpiredSessionToken({ status: 401 }, options), "expired-token")
  assert.equal(getExpiredSessionToken({ status: 503 }, options), "")
  assert.equal(getExpiredSessionToken({ status: 401 }, {}), "")
})
