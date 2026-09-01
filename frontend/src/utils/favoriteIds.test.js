import test from "node:test"
import assert from "node:assert/strict"

import { updateFavoriteIds } from "./favoriteIds.js"


test("adds and removes favorite property IDs immutably", () => {
  const current = new Set([1, 2])
  const added = updateFavoriteIds(current, "3", true)
  const removed = updateFavoriteIds(added, 2, false)

  assert.deepEqual([...current], [1, 2])
  assert.deepEqual([...added], [1, 2, 3])
  assert.deepEqual([...removed], [1, 3])
})
