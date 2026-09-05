export const REPORT_STATUSES = ["submitted", "reviewing", "resolved", "dismissed"]

export const REPORT_REASON_LABELS = {
  suspected_scam: "Posible estafa o fraude",
  misleading_information: "Información engañosa o incorrecta",
  duplicate_listing: "Anuncio duplicado",
  already_unavailable: "La propiedad ya no está disponible",
  inappropriate_content: "Contenido inapropiado",
  other: "Otro asunto de seguridad",
}

export function getModerationStatusOptions(status) {
  if (status === "submitted") return ["submitted", "reviewing", "resolved", "dismissed"]
  if (status === "reviewing") return ["reviewing", "resolved", "dismissed"]
  if (status === "resolved" || status === "dismissed") return [status]
  return []
}

export function getSafetyHoldAction(report) {
  if (
    !report
    || !Number.isInteger(report.property_id)
    || report.property_id <= 0
    || !Number.isInteger(report.listing_safety_version)
    || report.listing_safety_version <= 0
  ) return null

  const held = !report.listing_on_safety_hold
  return {
    held,
    label: held ? "Aplicar retención de seguridad" : "Liberar retención de seguridad",
  }
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

export function normalizeMyReportPage(data) {
  if (!data || typeof data !== "object") throw new Error("Invalid safety report response")
  const items = Array.isArray(data.items)
    ? data.items.filter((item) => (
      item
      && Number.isInteger(item.id)
      && item.id > 0
      && Number.isInteger(item.listing_id)
      && item.listing_id > 0
      && REPORT_STATUSES.includes(item.status)
    ))
    : []

  return {
    items,
    total: safeCount(data.total),
    page: Number.isInteger(data.page) && data.page > 0 ? data.page : 1,
    pageSize: Number.isInteger(data.page_size) && data.page_size > 0 ? data.page_size : 20,
    totalPages: Number.isInteger(data.total_pages) && data.total_pages > 0 ? data.total_pages : 1,
  }
}
