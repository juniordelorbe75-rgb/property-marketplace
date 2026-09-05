import test from "node:test"
import assert from "node:assert/strict"

import { getSourceHealth, normalizeDataSources } from "./dataSources.js"

test("normalizes valid source rows and safe inventory counts", () => {
  const sources = normalizeDataSources([
    { id: 1, name: "Aliado", source_key: "partner", total_listings: -2, public_listings: "4", stale_after_hours: 24 },
    { id: 0, name: "Inválido", source_key: "bad" },
  ])
  assert.equal(sources.length, 1)
  assert.equal(sources[0].total_listings, 0)
  assert.equal(sources[0].public_listings, 4)
})

test("classifies permission, freshness, and healthy source states", () => {
  const now = new Date("2026-09-05T12:00:00Z")
  assert.equal(getSourceHealth({ approved: false }, now).key, "permission")
  assert.equal(getSourceHealth({ approved: true, approval_status: "approved" }, now).key, "permission")
  assert.equal(getSourceHealth({ approved: true, approval_status: "approved", permission_document_url: "https://example.com/permission" }, now).key, "waiting")
  assert.equal(getSourceHealth({ approved: true, approval_status: "approved", permission_document_url: "https://example.com/permission", permission_expires_at: "2026-09-04T12:00:00Z" }, now).key, "expired")
  assert.equal(getSourceHealth({ approved: true, approval_status: "approved", permission_document_url: "https://example.com/permission", last_retrieved_at: "2026-09-01T12:00:00Z", stale_after_hours: 48 }, now).key, "stale")
  assert.equal(getSourceHealth({ approved: true, approval_status: "approved", permission_document_url: "https://example.com/permission", last_retrieved_at: "2026-09-05T11:00:00Z", stale_after_hours: 48 }, now).key, "healthy")
})
