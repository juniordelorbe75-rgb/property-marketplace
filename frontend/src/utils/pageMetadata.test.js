import test from "node:test"
import assert from "node:assert/strict"

import { pageTitleForPath } from "./pageMetadata.js"

test("provides Spanish titles for the main public and account routes", () => {
  assert.equal(pageTitleForPath("/"), "Propiedades en República Dominicana | HabitaRD")
  assert.equal(pageTitleForPath("/search"), "Buscar propiedades | HabitaRD")
  assert.equal(pageTitleForPath("/account/"), "Mi cuenta | HabitaRD")
  assert.equal(pageTitleForPath("/data-sources"), "Fuentes de datos | HabitaRD")
  assert.equal(pageTitleForPath("/data-partners"), "Fuentes y aliados de datos | HabitaRD")
})

test("uses safe generic titles for dynamic and unknown routes", () => {
  assert.equal(pageTitleForPath("/properties/HBRD-100"), "Detalle de propiedad | HabitaRD")
  assert.equal(pageTitleForPath("/profiles/42"), "Perfil público | HabitaRD")
  assert.equal(pageTitleForPath("/missing"), "Página no encontrada | HabitaRD")
})
