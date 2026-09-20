import test from "node:test"
import assert from "node:assert/strict"

import {
  buildRegistrationPayload,
} from "./registrationPayload.js"


const baseRegistration = {
  firstName: "June",
  middleName: "",
  lastName: "Gonzalez",
  dateOfBirth: "1995-01-15",
  bio: "",
  email: "  JUNE@example.com ",
  password: "secure-password-123",
}


test(
  "buyer registration sends account_type and never sends legacy role",
  () => {
    const payload =
      buildRegistrationPayload({
        ...baseRegistration,
        accountType: "buyer",

        sellerDetails: {
          seller_category: "agent",
          seller_phone:
            "+18095550123",
          business_name:
            "Hidden Business",
        },
      })

    assert.equal(
      payload.account_type,
      "buyer",
    )

    assert.equal(
      Object.hasOwn(
        payload,
        "role",
      ),
      false,
    )

    assert.equal(
      Object.hasOwn(
        payload,
        "seller_phone",
      ),
      false,
    )

    assert.equal(
      Object.hasOwn(
        payload,
        "seller_category",
      ),
      false,
    )

    assert.equal(
      payload.email,
      "june@example.com",
    )
  },
)


test(
  "seller registration includes normalized private seller information and verification proof",
  () => {
    const payload =
      buildRegistrationPayload({
        ...baseRegistration,

        accountType: "seller",

        sellerDetails: {
          seller_category: "owner",
          seller_phone:
            "+1 (809) 555-0123",
          business_name:
            "  Casa Norte  ",
        },

        phoneVerificationToken:
          "v".repeat(43),

        verifiedSellerPhone:
          "+18095550123",
      })

    assert.equal(
      payload.account_type,
      "seller",
    )

    assert.equal(
      payload.seller_category,
      "owner",
    )

    assert.equal(
      payload.seller_phone,
      "+18095550123",
    )

    assert.equal(
      payload.business_name,
      "Casa Norte",
    )

    assert.equal(
      payload.phone_verification_token,
      "v".repeat(43),
    )

    assert.equal(
      Object.hasOwn(
        payload,
        "role",
      ),
      false,
    )
  },
)


test(
  "seller registration cannot continue without verified phone proof",
  () => {
    assert.throws(
      () =>
        buildRegistrationPayload({
          ...baseRegistration,

          accountType:
            "seller",

          sellerDetails: {
            seller_category:
              "agent",

            seller_phone:
              "+18095550123",
          },
        }),
      /Verifique el teléfono/,
    )
  },
)


test(
  "seller registration rejects a phone changed after verification",
  () => {
    assert.throws(
      () =>
        buildRegistrationPayload({
          ...baseRegistration,

          accountType:
            "seller",

          sellerDetails: {
            seller_category:
              "developer",

            seller_phone:
              "+18295550123",
          },

          phoneVerificationToken:
            "v".repeat(43),

          verifiedSellerPhone:
            "+18095550123",
        }),
      /teléfono cambió/,
    )
  },
)