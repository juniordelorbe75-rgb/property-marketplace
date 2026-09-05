export function normalizeDataSources(payload) {
  if (!Array.isArray(payload)) return []
  return payload.filter((source) => (
    Number.isInteger(source?.id)
    && source.id > 0
    && typeof source.name === "string"
    && typeof source.source_key === "string"
  )).map((source) => ({
    ...source,
    total_listings: Math.max(0, Number(source.total_listings) || 0),
    public_listings: Math.max(0, Number(source.public_listings) || 0),
    stale_after_hours: Math.max(1, Number(source.stale_after_hours) || 48),
  }))
}

export function getSourceHealth(source, now = new Date()) {
  if (!source.approved || source.approval_status !== "approved") {
    return { key: "permission", label: "Sin permiso activo", detail: "No puede publicar inventario." }
  }
  if (!source.permission_document_url) {
    return { key: "permission", label: "Falta evidencia", detail: "El permiso aprobado no tiene documento verificable." }
  }
  const expiresAt = source.permission_expires_at ? new Date(source.permission_expires_at) : null
  if (expiresAt && !Number.isNaN(expiresAt.getTime()) && expiresAt <= now) {
    return { key: "expired", label: "Permiso vencido", detail: "El inventario debe permanecer oculto." }
  }
  const retrievedAt = source.last_retrieved_at ? new Date(source.last_retrieved_at) : null
  if (!retrievedAt || Number.isNaN(retrievedAt.getTime())) {
    return { key: "waiting", label: "Sin importaciones", detail: "El permiso está listo; falta recibir inventario." }
  }
  const staleAt = retrievedAt.getTime() + source.stale_after_hours * 60 * 60 * 1000
  if (staleAt <= now.getTime()) {
    return { key: "stale", label: "Datos desactualizados", detail: "La última importación superó el límite permitido." }
  }
  return { key: "healthy", label: "Lista para publicar", detail: "Permiso e inventario se encuentran vigentes." }
}
