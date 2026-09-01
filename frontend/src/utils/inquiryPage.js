import { propertyIdFromReference } from "./propertyReference.js"

export const EMPTY_INQUIRY_COUNTS = Object.freeze({
  all: 0,
  pending: 0,
  accepted: 0,
  rejected: 0,
  cancelled: 0,
})

export function buildInquiryPageUrl(kind, options = {}) {
  const params = new URLSearchParams({
    page: String(Math.max(1, Number(options.page) || 1)),
    page_size: String(Math.max(1, Number(options.pageSize) || 6)),
  })
  if (options.status && options.status !== "all") params.set("status", options.status)
  const propertyId = propertyIdFromReference(options.propertyReference)
  if (propertyId) params.set("property_id", String(propertyId))
  return `/inquiries/${kind}/page?${params}`
}

export function normalizeInquiryPage(data) {
  if (!data || !Array.isArray(data.items) || !data.counts) {
    throw new Error("The inquiry server returned an invalid page.")
  }
  return {
    items: data.items,
    total: Math.max(0, Number(data.total) || 0),
    page: Math.max(1, Number(data.page) || 1),
    pageSize: Math.max(1, Number(data.page_size) || 6),
    totalPages: Math.max(1, Number(data.total_pages) || 1),
    counts: { ...EMPTY_INQUIRY_COUNTS, ...data.counts },
  }
}
