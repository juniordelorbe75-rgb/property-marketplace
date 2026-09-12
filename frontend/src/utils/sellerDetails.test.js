import test from "node:test"
import assert from "node:assert/strict"
import { getSellerRegistrationFields } from "./sellerDetails.js"

test("switching to buyer never submits hidden seller contact details", () => {
  const details = { seller_category: "agent", seller_phone: "+1 809 555 0123", business_name: "Private Company" }
  assert.deepEqual(getSellerRegistrationFields("buyer", details), {})
  assert.deepEqual(getSellerRegistrationFields("", details), {})
})

test("seller submissions normalize phone formatting and trim optional business names", () => {
  assert.deepEqual(getSellerRegistrationFields("seller", {
    seller_category: "owner", seller_phone: "+1 (809) 555-0123", business_name: "  Casa Norte  ",
  }), { seller_category: "owner", seller_phone: "+18095550123", business_name: "Casa Norte" })
  assert.equal(getSellerRegistrationFields("seller", { seller_category: "agent", seller_phone: "+18095550123" }).business_name, "")
})

test("seller submissions reject missing categories and invalid contact numbers", () => {
  assert.throws(() => getSellerRegistrationFields("seller", {}), /tipo de vendedor/)
  for (const phone of ["", "8095550123", "+1", "+1809callme", "+1234567890123456"]) {
    assert.throws(() => getSellerRegistrationFields("seller", { seller_category: "agent", seller_phone: phone }), /teléfono válido/)
  }
})
