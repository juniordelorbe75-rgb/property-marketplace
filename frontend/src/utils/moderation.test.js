import test from "node:test"
import assert from "node:assert/strict"

import { getModerationStatusOptions, normalizeReportPage } from "./moderation.js"

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
