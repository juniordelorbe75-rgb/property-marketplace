import test from "node:test"
import assert from "node:assert/strict"

import {
  getModerationStatusOptions,
  getSafetyHoldAction,
  normalizeMyReportPage,
  normalizeReportPage,
} from "./moderation.js"

test("keeps closed moderation decisions terminal", () => {
  assert.deepEqual(getModerationStatusOptions("submitted"), [
    "submitted", "reviewing", "resolved", "dismissed",
  ])
  assert.deepEqual(getModerationStatusOptions("reviewing"), [
    "reviewing", "resolved", "dismissed",
  ])
  assert.deepEqual(getModerationStatusOptions("resolved"), ["resolved"])
  assert.deepEqual(getModerationStatusOptions("dismissed"), ["dismissed"])
})

test("normalizes report pages and rejects malformed report rows", () => {
  const page = normalizeReportPage({
    items: [
      { id: 7, version: 2, status: "reviewing" },
      { id: 0, version: 1, status: "submitted" },
      { id: 8, version: 0, status: "resolved" },
      { id: 9, version: 1, status: "unknown" },
    ],
    total: 4,
    page: 2,
    page_size: 20,
    total_pages: 3,
    counts: { all: 4, submitted: 2, reviewing: 1, resolved: -1 },
  })

  assert.deepEqual(page.items, [{ id: 7, version: 2, status: "reviewing" }])
  assert.equal(page.page, 2)
  assert.equal(page.totalPages, 3)
  assert.equal(page.counts.resolved, 0)
  assert.equal(page.counts.dismissed, 0)
})

test("keeps only valid private report-history rows", () => {
  const page = normalizeMyReportPage({
    items: [
      { id: 3, listing_id: 9, status: "resolved" },
      { id: 4, listing_id: 0, status: "submitted" },
      { id: 5, listing_id: 10, status: "unknown" },
    ],
    total: 3,
    page: 1,
    page_size: 20,
    total_pages: 1,
  })

  assert.deepEqual(page.items, [{ id: 3, listing_id: 9, status: "resolved" }])
  assert.equal(page.total, 3)
  assert.equal(page.totalPages, 1)
})

test("builds only valid reversible listing safety-hold actions", () => {
  assert.deepEqual(getSafetyHoldAction({
    property_id: 12,
    listing_safety_version: 3,
    listing_on_safety_hold: false,
  }), { held: true, label: "Aplicar retención de seguridad" })
  assert.deepEqual(getSafetyHoldAction({
    property_id: 12,
    listing_safety_version: 4,
    listing_on_safety_hold: true,
  }), { held: false, label: "Liberar retención de seguridad" })
  assert.equal(getSafetyHoldAction({ property_id: null, listing_safety_version: 1 }), null)
  assert.equal(getSafetyHoldAction({ property_id: 12, listing_safety_version: null }), null)
})
