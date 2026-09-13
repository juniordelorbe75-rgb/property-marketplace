import test from "node:test"
import assert from "node:assert/strict"

import {
  getCombinedResultPageCount,
  getExternalCatalogApiSearchParams,
} from "./externalCatalogSearch.js"

const baseSearch = {
  reference: "",
  location: "Santiago",
  minPrice: "100000",
  maxPrice: "300000",
  currency: "USD",
  propertyType: "Condo",
  listingType: "sale",
  amenity: "Pool",
  bedrooms: "2",
  bathrooms: "2",
  minSquareFeet: "1076.3910416709722",
  status: "available",
  sortBy: "price_low",
}

test("maps supported HabitaRD filters to the partner catalog", () => {
  const params = getExternalCatalogApiSearchParams(baseSearch, 3, 9)

  assert.equal(params.get("location"), "Santiago")
  assert.equal(params.get("currency"), "USD")
  assert.equal(params.get("amenity"), "Pool")
  assert.equal(Number(params.get("min_area_sqm")).toFixed(4), "100.0000")
  assert.equal(params.get("sort_by"), "price_low")
  assert.equal(params.get("limit"), "9")
  assert.equal(params.get("offset"), "18")
  assert.equal(params.has("status"), false)
})

test("does not mix partner inventory into a native listing reference search", () => {
  assert.equal(
    getExternalCatalogApiSearchParams({ ...baseSearch, reference: "PM-000123" }),
    null,
  )
})

test("does not show active partner inventory for unavailable-only searches", () => {
  assert.equal(
    getExternalCatalogApiSearchParams({ ...baseSearch, status: "unavailable" }),
    null,
  )
})

test("combined pagination follows whichever inventory has more pages", () => {
  assert.equal(getCombinedResultPageCount(3, 100, 9), 12)
  assert.equal(getCombinedResultPageCount(20, 1, 9), 3)
  assert.equal(getCombinedResultPageCount(0, 0, 9), 1)
})
