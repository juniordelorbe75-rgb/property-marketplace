import { propertyIdFromReference } from "./propertyReference.js"

export function filterInquiriesByProperty(inquiries, propertyReference) {
  const safeInquiries = Array.isArray(inquiries) ? inquiries : []
  const propertyId = propertyIdFromReference(propertyReference)

  if (!propertyId) return safeInquiries
  return safeInquiries.filter((inquiry) => Number(inquiry.property_id) === propertyId)
}
