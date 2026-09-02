import assert from "node:assert/strict"
import test from "node:test"

import { LOGIN_WELCOME_KEY, queueLoginWelcome } from "./loginWelcomeSession.js"

function memoryStorage() {
  const values = new Map()
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  }
}

test("queues distinct new and returning account welcomes", () => {
  const storage = memoryStorage()
  queueLoginWelcome("new", storage)
  assert.equal(storage.getItem(LOGIN_WELCOME_KEY), "new")
  queueLoginWelcome("returning", storage)
  assert.equal(storage.getItem(LOGIN_WELCOME_KEY), "returning")
})
