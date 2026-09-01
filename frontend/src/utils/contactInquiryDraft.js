const STORAGE_PREFIX = "property_marketplace_contact_draft_"
const UUID_PATTERN = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i

function storageFor(storage) {
  if (storage) return storage
  try { return globalThis.sessionStorage } catch { return null }
}

function storageKey(accountId, propertyId) {
  if (!/^\d+$/.test(String(accountId || "")) || !/^\d+$/.test(String(propertyId || ""))) {
    return ""
  }
  return `${STORAGE_PREFIX}${accountId}_${propertyId}`
}

function cleanDraft(value) {
  if (!value || typeof value !== "object") return null
  const message = typeof value.message === "string" ? value.message.slice(0, 1000) : ""
  const idempotencyKey = UUID_PATTERN.test(value.idempotencyKey || "")
    ? value.idempotencyKey
    : ""
  return message.trim() && idempotencyKey ? { message, idempotencyKey } : null
}

export function readContactInquiryDraft(accountId, propertyId, storage) {
  const target = storageFor(storage)
  const key = storageKey(accountId, propertyId)
  if (!target || !key) return null
  try { return cleanDraft(JSON.parse(target.getItem(key) || "null")) } catch { return null }
}

export function saveContactInquiryDraft(accountId, propertyId, draft, storage) {
  const target = storageFor(storage)
  const key = storageKey(accountId, propertyId)
  if (!target || !key) return
  try {
    const cleaned = cleanDraft(draft)
    if (cleaned) target.setItem(key, JSON.stringify(cleaned))
    else target.removeItem(key)
  } catch {
    // Contacting an owner remains usable when session storage is unavailable.
  }
}

export function clearContactInquiryDraft(accountId, propertyId, storage) {
  const target = storageFor(storage)
  const key = storageKey(accountId, propertyId)
  try { if (key) target?.removeItem(key) } catch {
    // Clearing a draft is best-effort.
  }
}
