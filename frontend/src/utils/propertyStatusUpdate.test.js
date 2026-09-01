import test from "node:test"
import assert from "node:assert/strict"

import { buildPropertyStatusUpdate } from "./propertyStatusUpdate.js"


test("changes only status while preserving the complete listing payload", () => {
  const property = {
    id: 4,
    title: "Lake House",
    description: "Near the water",
    image_url: "/uploads/property-images/cover.jpg",
    image_urls: ["/uploads/property-images/cover.jpg"],
    price: 420000,
    currency: "DOP",
    listing_type: "sale",
    amenities: ["Pool"],
    location: "Austin, Texas",
    property_type: "House",
    bedrooms: 3,
    bathrooms: 2,
    square_feet: 1800,
    status: "available",
  }

  const update = buildPropertyStatusUpdate(property, "unavailable")

  assert.equal(update.status, "unavailable")
  assert.equal(update.title, property.title)
  assert.equal(update.currency, "DOP")
  assert.deepEqual(update.image_urls, property.image_urls)
  assert.deepEqual(update.amenities, property.amenities)
  assert.equal("id" in update, false)
})
