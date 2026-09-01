import test from "node:test"
import assert from "node:assert/strict"
import { normalizePendingInquiryCount } from "./navbarStats.js"

test("normalizes seller pending inquiry counts for the navigation badge", () => {
  assert.equal(normalizePendingInquiryCount({ pending_inquiries: 4 }), 4)
  assert.equal(normalizePendingInquiryCount({ pending_inquiries: "2" }), 2)
  assert.equal(normalizePendingInquiryCount({ pending_inquiries: -1 }), 0)
  assert.equal(normalizePendingInquiryCount(null), 0)
})
