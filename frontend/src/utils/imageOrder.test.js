import test from "node:test"
import assert from "node:assert/strict"

import {
  getAdjacentImage,
  moveImageToCover,
  removeImageAt,
} from "./imageOrder.js"


test("moves a selected picture to the cover position", () => {
  const pictures = ["front.jpg", "kitchen.jpg", "yard.jpg"]

  assert.deepEqual(
    moveImageToCover(pictures, 2),
    ["yard.jpg", "front.jpg", "kitchen.jpg"],
  )
  assert.deepEqual(pictures, ["front.jpg", "kitchen.jpg", "yard.jpg"])
})

test("keeps image order safe for invalid selections", () => {
  assert.deepEqual(moveImageToCover(["front.jpg"], 4), ["front.jpg"])
  assert.deepEqual(moveImageToCover(null, 0), [])
})

test("removes only the selected picture without mutating the source", () => {
  const pictures = ["front.jpg", "kitchen.jpg", "yard.jpg"]

  assert.deepEqual(removeImageAt(pictures, 1), ["front.jpg", "yard.jpg"])
  assert.deepEqual(pictures, ["front.jpg", "kitchen.jpg", "yard.jpg"])
})

test("navigates property pictures circularly", () => {
  const pictures = ["front.jpg", "kitchen.jpg", "yard.jpg"]

  assert.equal(getAdjacentImage(pictures, "front.jpg", -1), "yard.jpg")
  assert.equal(getAdjacentImage(pictures, "yard.jpg", 1), "front.jpg")
  assert.equal(getAdjacentImage(pictures, "kitchen.jpg", 1), "yard.jpg")
  assert.equal(getAdjacentImage([], "front.jpg", 1), "")
})
