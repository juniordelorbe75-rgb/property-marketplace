export const SELLER_CATEGORIES = [
  {
    value: "owner",
    label: "Propietario",
  },
  {
    value: "agent",
    label: "Agente inmobiliario",
  },
  {
    value: "developer",
    label: "Desarrollador",
  },
]


export function getSellerCategoryLabel(value) {
  return (
    SELLER_CATEGORIES.find(
      (category) => category.value === value
    )?.label || "No indicado"
  )
}


export function compactSellerPhone(value) {
  return (value || "")
    .replace(/[\s().-]/g, "")
}


export function normalizeSellerPhone(value) {
  const phone = compactSellerPhone(value)

  if (
    !/^\+[1-9][0-9]{7,14}$/.test(phone)
  ) {
    throw new Error(
      "Incluya un teléfono válido con código de país, " +
      "por ejemplo +1 809 555 0123."
    )
  }

  return phone
}


export function getSellerRegistrationFields(
  accountType,
  details = {},
) {
  if (accountType !== "seller") {
    return {}
  }

  const categoryIsValid =
    SELLER_CATEGORIES.some(
      (category) =>
        category.value
        === details.seller_category
    )

  if (!categoryIsValid) {
    throw new Error(
      "Seleccione el tipo de vendedor."
    )
  }

  const phone =
    normalizeSellerPhone(
      details.seller_phone
    )

  return {
    seller_category:
      details.seller_category,

    seller_phone:
      phone,

    business_name:
      (details.business_name || "")
        .trim(),
  }
}