import test from "node:test"
import assert from "node:assert/strict"

import {
  formatPropertyReference,
  normalizePropertyReference,
  propertyIdFromReference,
} from "./propertyReference.js"


test("formats stable public marketplace references", () => {
  assert.equal(formatPropertyReference(42), "PM-000042")
  assert.equal(formatPropertyReference("invalid"), "")
})

test("accepts friendly numeric and prefixed reference searches", () => {
  assert.equal(normalizePropertyReference("42"), "PM-000042")
  assert.equal(normalizePropertyReference(" pm-000042 "), "PM-000042")
  assert.equal(normalizePropertyReference("other-42"), "")
})

test("extracts an internal id only from a valid property reference", () => {
  assert.equal(propertyIdFromReference("PM-000042"), 42)
  assert.equal(propertyIdFromReference("other-42"), null)
})
