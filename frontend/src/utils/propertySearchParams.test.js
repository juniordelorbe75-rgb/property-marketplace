import test from "node:test"
import assert from "node:assert/strict"

import {
  buildPropertySearchParams,
  getPropertyApiSearchParams,
  readPropertySearchParams,
} from "./propertySearchParams.js"

test("round trips buyer filters, sorting, and pagination", () => {
  const params = buildPropertySearchParams({
    reference: "42", location: " Miami ", minPrice: "1000", maxPrice: "2500",
    propertyType: "Condo", listingType: "rent", amenity: "Pool", currency: "DOP",
    bedrooms: "2", bathrooms: "2", minSquareFeet: "900",
    status: "available", sortBy: "price_low",
  }, 3)
  const search = readPropertySearchParams(params)

  assert.equal(search.location, "Miami")
  assert.equal(search.reference, "PM-000042")
  assert.equal(search.listingType, "rent")
  assert.equal(search.amenity, "Pool")
  assert.equal(search.currency, "DOP")
  assert.equal(search.sortBy, "price_low")
  assert.equal(search.page, 3)
})

test("rejects malformed or unsupported shared-link values", () => {
  const search = readPropertySearchParams(
    "min_price=-1&property_type=Castle&amenity=Unsafe&page=zero&sort_by=random",
  )

  assert.equal(search.minPrice, "")
  assert.equal(search.propertyType, "")
  assert.equal(search.amenity, "")
  assert.equal(search.page, 1)
  assert.equal(search.sortBy, "newest")
})

test("does not send client-only pagination to the API", () => {
  assert.equal(
    getPropertyApiSearchParams(new URLSearchParams("location=Austin&page=4")).toString(),
    "location=Austin",
  )
})

test("removes unsafe shared-link values before building an API request", () => {
  assert.equal(
    getPropertyApiSearchParams(
      new URLSearchParams("property_type=Castle&min_price=-50&status=available"),
    ).toString(),
    "status=available",
  )
})
