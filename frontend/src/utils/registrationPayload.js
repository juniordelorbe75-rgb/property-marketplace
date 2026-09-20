import { getSellerRegistrationFields } from "./sellerDetails.js"

export function buildRegistrationPayload(values) {
  const accountType = values.accountType === "seller" ? "seller" : "buyer"
  const payload = {
    account_type: accountType,
    first_name: values.firstName.trim(),
    middle_name: values.middleName.trim(),
    last_name: values.lastName.trim(),
    date_of_birth: values.dateOfBirth,
    bio: values.bio.trim(),
    email: values.email.trim(),
    password: values.password,
  }

  if (accountType === "seller") {
    const sellerFields = getSellerRegistrationFields(accountType, values.sellerDetails)
    if (!values.phoneVerificationToken || values.verifiedPhone !== sellerFields.seller_phone) {
      throw new Error("Valide el teléfono del vendedor antes de crear la cuenta.")
    }
    Object.assign(payload, sellerFields, {
      phone_verification_token: values.phoneVerificationToken,
    })
  }

  return payload
}
