import {
  getSellerRegistrationFields,
} from "./sellerDetails.js"


const ACCOUNT_TYPES = new Set([
  "buyer",
  "seller",
])


export function buildRegistrationPayload({
  accountType,
  firstName,
  middleName,
  lastName,
  dateOfBirth,
  bio,
  email,
  password,
  sellerDetails = {},
  phoneVerificationToken = "",
  verifiedSellerPhone = "",
}) {
  if (!ACCOUNT_TYPES.has(accountType)) {
    throw new Error(
      "Seleccione un tipo de cuenta válido."
    )
  }

  const payload = {
    account_type: accountType,

    first_name:
      (firstName || "").trim(),

    middle_name:
      (middleName || "").trim(),

    last_name:
      (lastName || "").trim(),

    date_of_birth:
      dateOfBirth,

    bio:
      (bio || "").trim(),

    email:
      (email || "")
        .trim()
        .toLowerCase(),

    password,
  }


  if (accountType !== "seller") {
    return payload
  }


  const sellerFields =
    getSellerRegistrationFields(
      accountType,
      sellerDetails,
    )


  if (!phoneVerificationToken) {
    throw new Error(
      "Verifique el teléfono del vendedor antes de crear la cuenta."
    )
  }


  if (
    !verifiedSellerPhone
    || verifiedSellerPhone
      !== sellerFields.seller_phone
  ) {
    throw new Error(
      "El teléfono cambió después de la verificación. " +
      "Envíe y confirme un código nuevo."
    )
  }


  return {
    ...payload,
    ...sellerFields,

    phone_verification_token:
      phoneVerificationToken,
  }
}