import test from "node:test"
import assert from "node:assert/strict"

import {
  compactSellerPhone,
  getSellerRegistrationFields,
  normalizeSellerPhone,
} from "./sellerDetails.js"


test(
  "buyer accounts never submit hidden seller details",
  () => {
    const details = {
      seller_category: "agent",
      seller_phone: "+1 809 555 0123",
      business_name: "Private Company",
    }

    assert.deepEqual(
      getSellerRegistrationFields(
        "buyer",
        details,
      ),
      {},
    )
  },
)


test(
  "seller submissions normalize phone formatting and business names",
  () => {
    assert.deepEqual(
      getSellerRegistrationFields(
        "seller",
        {
          seller_category: "owner",
          seller_phone:
            "+1 (809) 555-0123",

          business_name:
            "  Casa Norte  ",
        },
      ),
      {
        seller_category: "owner",
        seller_phone:
          "+18095550123",
        business_name:
          "Casa Norte",
      },
    )
  },
)


test(
  "seller registration rejects an invalid seller category",
  () => {
    assert.throws(
      () =>
        getSellerRegistrationFields(
          "seller",
          {
            seller_category:
              "invalid",

            seller_phone:
              "+18095550123",
          },
        ),
      /tipo de vendedor/,
    )
  },
)


test(
  "seller registration rejects invalid phone numbers",
  () => {
    const invalidPhones = [
      "",
      "8095550123",
      "+1",
      "+1809callme",
      "+1234567890123456",
    ]

    for (
      const phone
      of invalidPhones
    ) {
      assert.throws(
        () =>
          getSellerRegistrationFields(
            "seller",
            {
              seller_category:
                "agent",

              seller_phone:
                phone,
            },
          ),
        /teléfono válido/,
      )
    }
  },
)


test(
  "Dominican phone formatting is normalized",
  () => {
    assert.equal(
      normalizeSellerPhone(
        "+1 (809) 555-0123",
      ),
      "+18095550123",
    )

    assert.equal(
      normalizeSellerPhone(
        "+1 829 555 0123",
      ),
      "+18295550123",
    )

    assert.equal(
      normalizeSellerPhone(
        "+1-849-555-0123",
      ),
      "+18495550123",
    )
  },
)


test(
  "compactSellerPhone only removes formatting characters",
  () => {
    assert.equal(
      compactSellerPhone(
        "+1 (809) 555-0123",
      ),
      "+18095550123",
    )
  },
)