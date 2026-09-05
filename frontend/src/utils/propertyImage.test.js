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
    "Ocean View Condo — imagen 2",
  )
  assert.equal(getPropertyImageAlt("", 1), "Propiedad — imagen 1")
})

test("labels unavailable property pictures without exposing their URL", () => {
  assert.equal(
    getUnavailableImageLabel("Ocean View Condo"),
    "Imagen no disponible de Ocean View Condo",
  )
  assert.equal(getUnavailableImageLabel(), "Imagen no disponible de Propiedad")
})
