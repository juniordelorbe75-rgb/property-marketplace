import test from "node:test"
import assert from "node:assert/strict"
import { buildRegistrationPayload } from "./registrationPayload.js"

const fields = {
  firstName: " Ana ",
  middleName: " María ",
  lastName: " Pérez ",
  dateOfBirth: "1990-01-01",
  bio: " Hola ",
  email: " ANA@example.com ",
  password: "secure-password",
  sellerDetails: {
    seller_category: "owner",
    seller_phone: "+1 (809) 555-0123",
    business_name: " Casa Norte ",
  },
}

test("buyer registration sends account_type and excludes seller details", () => {
  const payload = buildRegistrationPayload({
    ...fields,
    accountType: "buyer",
    verifiedPhone: "+18095550123",
    phoneVerificationToken: "stale-token",
  })
  assert.equal(payload.account_type, "buyer")
  assert.equal(payload.first_name, "Ana")
  assert.equal(payload.email, "ANA@example.com")
  assert.equal("role" in payload, false)
  assert.equal("seller_phone" in payload, false)
  assert.equal("phone_verification_token" in payload, false)
})

test("seller registration includes normalized details and verified phone token", () => {
  const payload = buildRegistrationPayload({
    ...fields,
    accountType: "seller",
    verifiedPhone: "+18095550123",
    phoneVerificationToken: "verified-token",
  })
  assert.equal(payload.account_type, "seller")
  assert.equal(payload.seller_phone, "+18095550123")
  assert.equal(payload.business_name, "Casa Norte")
  assert.equal(payload.phone_verification_token, "verified-token")
})

test("seller registration rejects missing or stale phone verification", () => {
  for (const verifiedPhone of ["", "+18095550000"]) {
    assert.throws(() => buildRegistrationPayload({
      ...fields,
      accountType: "seller",
      verifiedPhone,
      phoneVerificationToken: "verified-token",
    }), /Valide el teléfono/)
  }
})
