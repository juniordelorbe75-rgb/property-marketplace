import test from "node:test"
import assert from "node:assert/strict"

import { filterInquiriesByProperty } from "./inquiryFilters.js"

const inquiries = [
  { id: 1, property_id: 42 },
  { id: 2, property_id: 7 },
]

test("filters inquiries using a public property reference", () => {
  assert.deepEqual(filterInquiriesByProperty(inquiries, "PM-000042"), [inquiries[0]])
  assert.deepEqual(filterInquiriesByProperty(inquiries, "7"), [inquiries[1]])
})

test("leaves inquiries visible when the property reference is invalid", () => {
  assert.deepEqual(filterInquiriesByProperty(inquiries, "not-a-reference"), inquiries)
  assert.deepEqual(filterInquiriesByProperty(null, "PM-000042"), [])
})
