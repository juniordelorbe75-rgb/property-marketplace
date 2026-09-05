import assert from "node:assert/strict"
import { readFileSync } from "node:fs"
import test from "node:test"

const indexHtml = readFileSync(new URL("../../index.html", import.meta.url), "utf8")
const headers = readFileSync(new URL("../../public/_headers", import.meta.url), "utf8")

test("frontend policy blocks injected scripts, framing, and browser device access", () => {
  assert.doesNotMatch(indexHtml, /http-equiv="Content-Security-Policy"/)
  assert.match(headers, /script-src 'self'/)
  assert.match(headers, /object-src 'none'/)
  assert.match(headers, /base-uri 'self'/)
  assert.match(headers, /frame-ancestors 'none'/)
  assert.match(headers, /Permissions-Policy: camera=\(\), microphone=\(\), geolocation=\(\), payment=\(\)/)
})

test("licensed property images remain available without allowing remote scripts", () => {
  assert.match(headers, /img-src 'self' data: blob: https:/)
  assert.doesNotMatch(headers, /script-src[^;]*https:/)
  assert.match(headers, /\/assets\/\*/)
  assert.match(headers, /max-age=31536000, immutable/)
})
