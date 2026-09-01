import test from "node:test"
import assert from "node:assert/strict"

import {
  clearListingDraft,
  createListingKey,
  getDraftOwnerId,
  hasListingDraft,
  readListingDraft,
  saveListingDraft,
} from "./listingDraft.js"

function memoryStorage() {
  const values = new Map()
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  }
}

function tokenFor(subject) {
  const payload = btoa(JSON.stringify({ sub: subject }))
    .replace(/=/g, "").replace(/\+/g, "-").replace(/\//g, "_")
  return `header.${payload}.signature`
}

test("derives only numeric owner namespaces from tokens", () => {
  assert.equal(getDraftOwnerId(tokenFor("42")), "42")
  assert.equal(getDraftOwnerId(tokenFor("not-an-id")), "")
  assert.equal(getDraftOwnerId("broken"), "")
})

test("creates API-compatible listing identity keys", () => {
  assert.match(
    createListingKey(),
    /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i,
  )
})

test("stores validated drafts separately for each seller", () => {
  const storage = memoryStorage()
  saveListingDraft("1", {
    title: "Seller One Home", amenities: ["Pool", "Unknown"],
    listingType: "rent", bathrooms: "2", status: "available",
    idempotencyKey: createListingKey(),
  }, storage)
  saveListingDraft("2", {
    title: "Seller Two Home", amenities: [], bathrooms: "1",
  }, storage)

  assert.equal(readListingDraft("1", storage).title, "Seller One Home")
  assert.deepEqual(readListingDraft("1", storage).amenities, ["Pool"])
  assert.equal(readListingDraft("2", storage).title, "Seller Two Home")
  assert.equal(hasListingDraft(readListingDraft("1", storage)), true)

  clearListingDraft("1", storage)
  assert.equal(readListingDraft("1", storage), null)
  assert.equal(readListingDraft("2", storage).title, "Seller Two Home")
})
