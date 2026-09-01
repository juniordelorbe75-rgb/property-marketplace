import test from "node:test"
import assert from "node:assert/strict"
import {
  buildInquiryPageUrl,
  buildInquiryReadReceipts,
  normalizeInquiryPage,
} from "./inquiryPage.js"

test("builds bounded server inquiry pagination and filters", () => {
  assert.equal(
    buildInquiryPageUrl("sent", { page: 2, pageSize: 6, status: "pending", propertyReference: "PM-000042" }),
    "/inquiries/sent/page?page=2&page_size=6&status=pending&property_id=42",
  )
  assert.equal(
    buildInquiryPageUrl("received", { page: -4, status: "all", propertyReference: "invalid" }),
    "/inquiries/received/page?page=1&page_size=6",
  )
})

test("normalizes an authoritative inquiry page and rejects malformed data", () => {
  const page = normalizeInquiryPage({
    items: [{ id: 1 }], total: 1, page: 1, page_size: 6, total_pages: 1,
    counts: { all: 1, pending: 1, accepted: 0, rejected: 0, cancelled: 0 },
  })
  assert.equal(page.counts.pending, 1)
  assert.equal(page.pageSize, 6)
  assert.throws(() => normalizeInquiryPage({ items: [] }), /invalid page/)
})

test("builds read receipts only for valid unread inquiry snapshots", () => {
  assert.deepEqual(buildInquiryReadReceipts([
    { id: 7, unread_count: 2, read_through_at: "2026-08-31T10:00:00Z" },
    { id: 8, unread_count: 0, read_through_at: "2026-08-31T10:00:00Z" },
    { id: -1, unread_count: 1, read_through_at: "2026-08-31T10:00:00Z" },
    { id: 9, unread_count: 1, read_through_at: "not-a-date" },
  ]), [{
    inquiry_id: 7,
    read_through_at: "2026-08-31T10:00:00Z",
  }])
})

test("deduplicates receipts at the newest delivered boundary", () => {
  assert.deepEqual(buildInquiryReadReceipts([
    { id: 12, unread_count: 1, read_through_at: "2026-08-31T10:00:00Z" },
    { id: 12, unread_count: 1, read_through_at: "2026-08-31T10:05:00Z" },
  ]), [{
    inquiry_id: 12,
    read_through_at: "2026-08-31T10:05:00Z",
  }])
})
