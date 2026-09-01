import test from "node:test"
import assert from "node:assert/strict"

import { DOMINICAN_PROVINCES } from "./dominicanLocations.js"


test("provides every Dominican province and the National District once", () => {
  assert.equal(DOMINICAN_PROVINCES.length, 32)
  assert.equal(new Set(DOMINICAN_PROVINCES).size, 32)
  for (const location of [
    "Distrito Nacional",
    "La Altagracia",
    "Puerto Plata",
    "Santiago",
    "Santo Domingo",
  ]) {
    assert.equal(DOMINICAN_PROVINCES.includes(location), true)
  }
})
