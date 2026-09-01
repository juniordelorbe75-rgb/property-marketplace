import test from "node:test"
import assert from "node:assert/strict"

import { getReturnPath, getSafeReturnPath } from "./authRedirect.js"

test("builds a return path from the current route", () => {
  assert.equal(
    getReturnPath({ pathname: "/properties/42", search: "?view=gallery", hash: "#contact" }),
    "/properties/42?view=gallery#contact",
  )
})

test("accepts local return paths", () => {
  assert.equal(getSafeReturnPath("/inquiries?status=pending"), "/inquiries?status=pending")
})

test("rejects external and protocol-relative return destinations", () => {
  assert.equal(getSafeReturnPath("https://example.com/steal-token"), "/")
  assert.equal(getSafeReturnPath("//example.com/steal-token"), "/")
  assert.equal(getSafeReturnPath(null), "/")
})
