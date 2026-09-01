import test from "node:test"
import assert from "node:assert/strict"
import { normalizeUnreadInquiryCount } from "./navbarStats.js"

test("normalizes unread inquiry counts for the navigation badge", () => {
  assert.equal(normalizeUnreadInquiryCount({ unread_count: 4 }), 4)
  assert.equal(normalizeUnreadInquiryCount({ unread_count: "2" }), 2)
  assert.equal(normalizeUnreadInquiryCount({ unread_count: -1 }), 0)
  assert.equal(normalizeUnreadInquiryCount(null), 0)
})
