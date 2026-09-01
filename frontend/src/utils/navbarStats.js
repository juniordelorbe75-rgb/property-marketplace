export function normalizePendingInquiryCount(stats) {
  const count = Number(stats?.pending_inquiries)
  return Number.isSafeInteger(count) && count > 0 ? count : 0
}
