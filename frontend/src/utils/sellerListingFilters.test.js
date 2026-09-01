import test from "node:test"
import assert from "node:assert/strict"
import { countSellerListingFilters, filterSellerListings } from "./sellerListingFilters.js"

const properties = [
  { id: 7, title: "Garden Villa", location: "Santiago", status: "available" },
  { id: 42, title: "Ocean Apartment", location: "Punta Cana", status: "unavailable" },
]
const engagement = { 7: { pending_inquiries: 2 }, 42: { pending_inquiries: 0 } }

test("filters seller listings by availability and pending attention", () => {
  assert.deepEqual(filterSellerListings(properties, engagement, "", "available"), [properties[0]])
  assert.deepEqual(filterSellerListings(properties, engagement, "", "attention"), [properties[0]])
  assert.deepEqual(filterSellerListings(properties, engagement, "", "unsupported"), properties)
})

test("finds seller listings by title, location, or public reference", () => {
  assert.deepEqual(filterSellerListings(properties, engagement, "ocean", "all"), [properties[1]])
  assert.deepEqual(filterSellerListings(properties, engagement, "santiago", "all"), [properties[0]])
  assert.deepEqual(filterSellerListings(properties, engagement, "pm-000042", "all"), [properties[1]])
})

test("counts seller listing filters from current dashboard data", () => {
  assert.deepEqual(countSellerListingFilters(properties, engagement), {
    all: 2,
    available: 1,
    unavailable: 1,
    attention: 1,
  })
})
