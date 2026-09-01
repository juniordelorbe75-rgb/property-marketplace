import test from "node:test"
import assert from "node:assert/strict"
import {
  clearContactInquiryDraft,
  readContactInquiryDraft,
  saveContactInquiryDraft,
} from "./contactInquiryDraft.js"

const KEY = "123e4567-e89b-42d3-a456-426614174000"

function memoryStorage() {
  const values = new Map()
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
    removeItem: (key) => values.delete(key),
  }
}

test("keeps contact drafts isolated by account and property", () => {
  const storage = memoryStorage()
  saveContactInquiryDraft("4", "12", { message: "First home", idempotencyKey: KEY }, storage)
  saveContactInquiryDraft("4", "19", { message: "Second home", idempotencyKey: KEY }, storage)
  assert.equal(readContactInquiryDraft("4", "12", storage).message, "First home")
  assert.equal(readContactInquiryDraft("4", "19", storage).message, "Second home")
  assert.equal(readContactInquiryDraft("8", "12", storage), null)
})

test("requires a valid retry identity and bounds message length", () => {
  const storage = memoryStorage()
  saveContactInquiryDraft("4", "12", { message: "x".repeat(1200), idempotencyKey: KEY }, storage)
  assert.equal(readContactInquiryDraft("4", "12", storage).message.length, 1000)
  saveContactInquiryDraft("4", "12", { message: "Unsafe retry", idempotencyKey: "bad" }, storage)
  assert.equal(readContactInquiryDraft("4", "12", storage), null)
})

test("clears a completed contact draft", () => {
  const storage = memoryStorage()
  saveContactInquiryDraft("4", "12", { message: "Question", idempotencyKey: KEY }, storage)
  clearContactInquiryDraft("4", "12", storage)
  assert.equal(readContactInquiryDraft("4", "12", storage), null)
})
