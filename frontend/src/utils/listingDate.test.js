import test from "node:test"
import assert from "node:assert/strict"

import { formatListingDate, getListingFreshness } from "./listingDate.js"


test("labels new and edited listings from authoritative timestamps", () => {
  const created = "2026-08-20T10:00:00Z"

  assert.match(getListingFreshness(created, created), /^Publicada /)
  assert.match(
    getListingFreshness(created, "2026-08-21T10:00:00Z"),
    /^Actualizada /,
  )
})

test("ignores invalid listing timestamps", () => {
  assert.equal(formatListingDate("not-a-date"), "")
  assert.equal(getListingFreshness("not-a-date", "2026-08-21"), "")
})
