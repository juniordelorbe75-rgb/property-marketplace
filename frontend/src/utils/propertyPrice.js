export function formatPropertyPrice(price, currency = "USD", listingType = "sale") {
  const amount = Number(price)
  if (!Number.isFinite(amount)) return ""

  const prefix = currency === "DOP" ? "RD$" : "US$"
  const suffix = listingType === "rent" ? "/month" : ""
  return `${prefix}${amount.toLocaleString()}${suffix}`
}
