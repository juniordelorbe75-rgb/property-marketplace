import test from "node:test"
import assert from "node:assert/strict"

import { formatPropertyPrice } from "./propertyPrice.js"


test("formats Dominican peso and US dollar property prices clearly", () => {
  assert.equal(formatPropertyPrice(3500000, "DOP"), "RD$3,500,000")
  assert.equal(formatPropertyPrice(2200, "USD", "rent"), "US$2,200/month")
  assert.equal(formatPropertyPrice("invalid", "DOP"), "")
})
