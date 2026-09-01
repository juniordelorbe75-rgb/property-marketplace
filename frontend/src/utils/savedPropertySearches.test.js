import test from "node:test"
import assert from "node:assert/strict"

import {
  describePropertySearch,
  readSavedPropertySearches,
  removeSavedPropertySearch,
  savePropertySearch,
} from "./savedPropertySearches.js"

function memoryStorage(initial = {}) {
  const values = new Map(Object.entries(initial))
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  }
}

test("saves canonical searches, removes pages, and deduplicates", () => {
  const storage = memoryStorage()
  savePropertySearch(storage, "location=Miami&page=4&property_type=House")
  const saved = savePropertySearch(storage, "property_type=House&location=Miami")

  assert.equal(saved.length, 1)
  assert.equal(saved[0].query, "location=Miami&property_type=House")
  assert.match(saved[0].label, /Miami/)
  assert.match(saved[0].label, /House/)
})

test("rejects corrupt storage and unsupported saved filters", () => {
  const corrupt = memoryStorage({ property_marketplace_saved_searches: "not json" })
  const unsupported = memoryStorage({
    property_marketplace_saved_searches: JSON.stringify([
      { query: "property_type=Castle" },
    ]),
  })

  assert.deepEqual(readSavedPropertySearches(corrupt), [])
  assert.deepEqual(readSavedPropertySearches(unsupported), [])
})

test("describes and removes saved searches", () => {
  const storage = memoryStorage()
  const saved = savePropertySearch(storage, "listing_type=rent&bedrooms=2&max_price=3000&currency=DOP")

  assert.equal(
    describePropertySearch(saved[0].query),
    "For Rent · Dominican Pesos · Up to RD$3,000 · 2+ beds",
  )
  assert.deepEqual(removeSavedPropertySearch(storage, saved[0].query), [])
})
