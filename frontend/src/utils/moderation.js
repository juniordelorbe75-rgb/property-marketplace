export const REPORT_STATUSES = ["submitted", "reviewing", "resolved", "dismissed"]

export const REPORT_REASON_LABELS = {
  suspected_scam: "Suspected scam or fraud",
  misleading_information: "Misleading or incorrect information",
  duplicate_listing: "Duplicate listing",
  already_unavailable: "Property is no longer available",
  inappropriate_content: "Inappropriate content",
  other: "Other safety concern",
}

export function getModerationStatusOptions(status) {
  if (status === "submitted") return ["submitted", "reviewing", "resolved", "dismissed"]
  if (status === "reviewing") return ["reviewing", "resolved", "dismissed"]
  if (status === "resolved" || status === "dismissed") return [status]
  return []
}

function safeCount(value) {
  return Number.isInteger(value) && value >= 0 ? value : 0
}

export function normalizeReportPage(data) {
  if (!data || typeof data !== "object") throw new Error("Invalid safety report response")
  const items = Array.isArray(data.items)
    ? data.items.filter((item) => (
      item
      && Number.isInteger(item.id)
      && item.id > 0
      && Number.isInteger(item.version)
      && item.version > 0
      && REPORT_STATUSES.includes(item.status)
    ))
    : []
  const page = Number.isInteger(data.page) && data.page > 0 ? data.page : 1
  const totalPages = Number.isInteger(data.total_pages) && data.total_pages > 0
    ? data.total_pages
    : 1

  return {
    items,
    total: safeCount(data.total),
    page,
    pageSize: Number.isInteger(data.page_size) && data.page_size > 0 ? data.page_size : 20,
    totalPages,
    counts: {
      all: safeCount(data.counts?.all),
      submitted: safeCount(data.counts?.submitted),
      reviewing: safeCount(data.counts?.reviewing),
      resolved: safeCount(data.counts?.resolved),
      dismissed: safeCount(data.counts?.dismissed),
    },
  }
}
