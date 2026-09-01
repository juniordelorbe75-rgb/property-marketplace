export const INQUIRIES_CHANGED_EVENT = "marketplace:inquiries-changed"
export function notifyInquiriesChanged() { window.dispatchEvent(new Event(INQUIRIES_CHANGED_EVENT)) }
