import test from "node:test"
import assert from "node:assert/strict"
import { readInquiryDrafts, saveInquiryDrafts } from "./inquiryDrafts.js"

function memoryStorage() {
  const values = new Map()
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  }
}

test("stores inquiry drafts separately for each signed-in account", () => {
  const storage = memoryStorage()
  saveInquiryDrafts("12", { 4: "Buyer draft" }, storage)
  saveInquiryDrafts("19", { 7: "Seller draft" }, storage)
  assert.deepEqual(readInquiryDrafts("12", storage), { 4: "Buyer draft" })
  assert.deepEqual(readInquiryDrafts("19", storage), { 7: "Seller draft" })
})

test("removes empty drafts and rejects malformed stored values", () => {
  const storage = memoryStorage()
  saveInquiryDrafts("12", { 4: "   ", invalid: "hidden" }, storage)
  assert.deepEqual(readInquiryDrafts("12", storage), {})
  assert.deepEqual(readInquiryDrafts("not-an-account", storage), {})
})

test("bounds restored draft text to the API message limit", () => {
  const storage = memoryStorage()
  saveInquiryDrafts("12", { 4: "x".repeat(1200) }, storage)
  assert.equal(readInquiryDrafts("12", storage)[4].length, 1000)
})
