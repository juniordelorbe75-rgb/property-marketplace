import test from "node:test"
import assert from "node:assert/strict"

import { getConnectivityNotice, getConnectivityState } from "./connectivity.js"


test("treats only an explicit offline signal as offline", () => {
  assert.equal(getConnectivityState(false), "offline")
  assert.equal(getConnectivityState(true), "online")
  assert.equal(getConnectivityState(undefined), "online")
})

test("provides clear notices only when connection state needs attention", () => {
  assert.match(getConnectivityNotice("offline").message, /changes cannot be sent/i)
  assert.match(getConnectivityNotice("restored").message, /connection restored/i)
  assert.equal(getConnectivityNotice("online"), null)
})
