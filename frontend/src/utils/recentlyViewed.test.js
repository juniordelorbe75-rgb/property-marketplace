import test from "node:test"
import assert from "node:assert/strict"

import {
  clearRecentlyViewed,
  readRecentlyViewed,
  rememberRecentlyViewed,
} from "./recentlyViewed.js"

function memoryStorage() {
  const values = new Map()
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  }
}

function property(id) {
  return {
    id, title: `Home ${id}`, location: "Austin", property_type: "House",
    status: "available", listing_type: "sale", image_url: "", price: id * 100,
    bedrooms: 3, bathrooms: 2, square_feet: 1500, owner_id: 42,
  }
}

test("keeps the six most recent unique properties", () => {
  const storage = memoryStorage()
  for (let id = 1; id <= 7; id += 1) rememberRecentlyViewed(property(id), storage)
  rememberRecentlyViewed(property(5), storage)

  assert.deepEqual(readRecentlyViewed(storage).map((item) => item.id), [5, 7, 6, 4, 3, 2])
  assert.equal(readRecentlyViewed(storage)[0].owner_id, 42)
})

test("ignores corrupt data and tolerates unavailable storage", () => {
  const corrupt = { getItem: () => "not-json" }
  const blocked = {
    getItem: () => { throw new Error("blocked") },
    setItem: () => { throw new Error("blocked") },
    removeItem: () => { throw new Error("blocked") },
  }

  assert.deepEqual(readRecentlyViewed(corrupt), [])
  assert.doesNotThrow(() => rememberRecentlyViewed(property(1), blocked))
  assert.doesNotThrow(() => clearRecentlyViewed(blocked))
})
