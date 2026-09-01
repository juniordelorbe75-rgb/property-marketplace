export function getApiError(data, fallbackMessage) {
  const detail = data?.detail
  const supportId = typeof data?.request_id === "string" && data.request_id
    ? ` Support ID: ${data.request_id}`
    : ""

  if (typeof detail === "string" && detail.trim()) {
    return `${detail}${supportId}`
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => item?.msg)
      .filter(Boolean)

    if (messages.length > 0) {
      return `${messages.join(" ")}${supportId}`
    }
  }

  return `${fallbackMessage}${supportId}`
}
