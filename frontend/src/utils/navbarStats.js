export function normalizeUnreadInquiryCount(stats) {
  const count = Number(stats?.unread_count)
  return Number.isSafeInteger(count) && count > 0 ? count : 0
}
