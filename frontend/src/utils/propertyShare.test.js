import test from "node:test"
import assert from "node:assert/strict"

import { buildPropertyShareUrl, shareProperty } from "./propertyShare.js"

const property = { id: 42, title: "Lake House", location: "Austin, Texas" }

test("builds a canonical listing URL without search or hash state", () => {
  assert.equal(
    buildPropertyShareUrl(42, "https://market.example/search?q=lake#results"),
    "https://market.example/properties/42",
  )
})

test("prefers the native share sheet with public listing details", async () => {
  let shared
  const result = await shareProperty(
    property,
    { share: async (data) => { shared = data } },
    "https://market.example/properties/42?from=search",
  )

  assert.equal(result.method, "native")
  assert.equal(shared.title, "Lake House")
  assert.equal(shared.url, "https://market.example/properties/42")
})

test("falls back to clipboard and then a manual link", async () => {
  let copied = ""
  const clipboardResult = await shareProperty(
    property,
    { clipboard: { writeText: async (value) => { copied = value } } },
    "https://market.example/",
  )
  const manualResult = await shareProperty(property, {}, "https://market.example/")

  assert.equal(clipboardResult.method, "clipboard")
  assert.equal(copied, "https://market.example/properties/42")
  assert.equal(manualResult.method, "manual")
  assert.equal(manualResult.url, copied)
})
