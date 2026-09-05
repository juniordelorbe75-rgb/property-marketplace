export function formatListingDate(value) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) return ""

  return new Intl.DateTimeFormat("es-DO", {
    year: "numeric",
    month: "short",
    day: "numeric",
  }).format(date)
}

export function getListingFreshness(createdAt, updatedAt) {
  const createdTime = new Date(createdAt).getTime()
  const updatedTime = new Date(updatedAt).getTime()

  if (!Number.isFinite(createdTime)) return ""

  const wasUpdated = Number.isFinite(updatedTime) && updatedTime > createdTime
  const value = wasUpdated ? updatedAt : createdAt
  const formatted = formatListingDate(value)

  return formatted ? `${wasUpdated ? "Actualizada" : "Publicada"} ${formatted}` : ""
}
