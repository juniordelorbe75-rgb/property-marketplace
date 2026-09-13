import test from "node:test"
import assert from "node:assert/strict"

import { resolveApiUrl } from "./apiUrl.js"


test("adds the hosted API origin only to local API paths", () => {
  assert.equal(
    resolveApiUrl("/properties/", "https://habitard-api.example"),
    "https://habitard-api.example/properties/",
  )
  assert.equal(
    resolveApiUrl("/auth/providers", "https://habitard-api.example/"),
    "https://habitard-api.example/auth/providers",
  )
  assert.equal(
    resolveApiUrl("https://images.example/home.jpg", "https://habitard-api.example"),
    "https://images.example/home.jpg",
  )
  assert.equal(resolveApiUrl("/properties/", ""), "/properties/")
})
