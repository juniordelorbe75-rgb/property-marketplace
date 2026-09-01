import test from "node:test"
import assert from "node:assert/strict"

import {
  buildSearchPageShareUrl,
  shareSearchPage,
} from "./searchPageShare.js"


test("shares only validated property filters and the current results page", () => {
  assert.equal(
    buildSearchPageShareUrl(
      "https://market.example/private?location=Miami&property_type=Castle&page=3#results",
    ),
    "https://market.example/?location=Miami&page=3",
  )
})

test("uses native sharing and preserves the canonical search URL", async () => {
  let shared
  const result = await shareSearchPage(
    { share: async (data) => { shared = data } },
    "https://market.example/?listing_type=rent&bedrooms=2",
  )

  assert.equal(result.method, "native")
  assert.equal(shared.url, "https://market.example/?listing_type=rent&bedrooms=2")
})

test("falls back from clipboard to manual search-page sharing", async () => {
  let copied
  const clipboard = await shareSearchPage(
    { clipboard: { writeText: async (url) => { copied = url } } },
    "https://market.example/?status=available",
  )
  const manual = await shareSearchPage({}, "https://market.example/")

  assert.equal(clipboard.method, "clipboard")
  assert.equal(copied, "https://market.example/?status=available")
  assert.equal(manual.method, "manual")
})
