import test from "node:test"
import assert from "node:assert/strict"

import { indexPropertyEngagement } from "./propertyEngagement.js"


test("indexes validated seller engagement by property", () => {
  assert.deepEqual(indexPropertyEngagement([
    { property_id: 4, favorites: 3, inquiries: 2, pending_inquiries: 1 },
    { property_id: "bad", favorites: 100 },
  ]), {
    4: { favorites: 3, inquiries: 2, pending_inquiries: 1 },
  })
})
