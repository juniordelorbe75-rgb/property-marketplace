const STORAGE_PREFIX = "property_marketplace_inquiry_drafts_"

function storageFor(storage) {
  if (storage) return storage
  try { return globalThis.sessionStorage } catch { return null }
}

function validAccountId(accountId) {
  return /^\d+$/.test(String(accountId || ""))
}

function cleanDrafts(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) return {}
  return Object.fromEntries(
    Object.entries(value)
      .filter(([inquiryId, message]) => /^\d+$/.test(inquiryId) && typeof message === "string")
      .slice(0, 50)
      .map(([inquiryId, message]) => [inquiryId, message.slice(0, 1000)])
      .filter(([, message]) => message.trim()),
  )
}

export function readInquiryDrafts(accountId, storage) {
  const target = storageFor(storage)
  if (!target || !validAccountId(accountId)) return {}
  try {
    return cleanDrafts(JSON.parse(target.getItem(`${STORAGE_PREFIX}${accountId}`) || "null"))
  } catch {
    return {}
  }
}

export function saveInquiryDrafts(accountId, drafts, storage) {
  const target = storageFor(storage)
  if (!target || !validAccountId(accountId)) return
  try {
    const key = `${STORAGE_PREFIX}${accountId}`
    const cleaned = cleanDrafts(drafts)
    if (Object.keys(cleaned).length) target.setItem(key, JSON.stringify(cleaned))
    else target.removeItem(key)
  } catch {
    // Messaging remains usable when session storage is unavailable.
  }
}
