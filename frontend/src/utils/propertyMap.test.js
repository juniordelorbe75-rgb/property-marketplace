import test from "node:test"
import assert from "node:assert/strict"

import { buildPropertyMapUrl, isMapLocationDetailed } from "./propertyMap.js"


test("builds an encoded map search from Dominican location text", () => {
  const url = new URL(buildPropertyMapUrl("Piantini, Distrito Nacional"))

  assert.equal(url.origin, "https://www.google.com")
  assert.equal(url.pathname, "/maps/search/")
  assert.equal(url.searchParams.get("api"), "1")
  assert.equal(url.searchParams.get("query"), "Piantini, Distrito Nacional")
})

test("does not create a map link for a missing location", () => {
  assert.equal(buildPropertyMapUrl("   "), "")
  assert.equal(buildPropertyMapUrl(null), "")
})

test("identifies location text that gives map search useful context", () => {
  assert.equal(isMapLocationDetailed("cotui"), false)
  assert.equal(isMapLocationDetailed("Cotuí, Sánchez Ramírez"), true)
  assert.equal(isMapLocationDetailed(" , Dominican Republic"), false)
})
