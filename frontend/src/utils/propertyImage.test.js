import test from "node:test"
import assert from "node:assert/strict"

import {
  getPropertyImageAlt,
  getUnavailableImageLabel,
} from "./propertyImage.js"


test("builds useful property image alternative text", () => {
  assert.equal(getPropertyImageAlt("Ocean View Condo"), "Ocean View Condo")
  assert.equal(
    getPropertyImageAlt("Ocean View Condo", 2),
    "Ocean View Condo — picture 2",
  )
  assert.equal(getPropertyImageAlt("", 1), "Property — picture 1")
})

test("labels unavailable property pictures without exposing their URL", () => {
  assert.equal(
    getUnavailableImageLabel("Ocean View Condo"),
    "Ocean View Condo picture unavailable",
  )
  assert.equal(getUnavailableImageLabel(), "Property picture unavailable")
})
