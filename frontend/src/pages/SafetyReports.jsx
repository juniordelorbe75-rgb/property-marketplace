import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"

import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { formatPropertyReference } from "../utils/propertyReference"
import {
  getModerationStatusOptions,
  getSafetyHoldAction,
  normalizeReportPage,
  REPORT_REASON_LABELS,
  REPORT_STATUSES,
} from "../utils/moderation"
import "./SafetyReports.css"

const STATUS_LABELS = {
  submitted: "Recibido",
  reviewing: "En revisión",
  resolved: "Resuelto",
  dismissed: "Desestimado",
}

const EMPTY_PAGE = {
  items: [],
  total: 0,
  page: 1,
  pageSize: 20,
  totalPages: 1,
  counts: { all: 0, submitted: 0, reviewing: 0, resolved: 0, dismissed: 0 },
}

function formatReportDate(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? "Fecha no disponible" : date.toLocaleString("es-DO")
}

function SafetyReports() {
  const { token } = useAuth()
  const [reportPage, setReportPage] = useState(EMPTY_PAGE)
  const [statusFilter, setStatusFilter] = useState("submitted")
  const [page, setPage] = useState(1)
  const [drafts, setDrafts] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [accessDenied, setAccessDenied] = useState(false)
  const [updatingId, setUpdatingId] = useState(null)
  const [holdingId, setHoldingId] = useState(null)
  const [loadAttempt, setLoadAttempt] = useState(0)

  const loadReports = useCallback(async (signal) => {
    if (!token) return
    setLoading(true)
    setError("")
    setAccessDenied(false)

    try {
      const query = new URLSearchParams({ page: String(page), page_size: "20" })
      if (statusFilter) query.set("status", statusFilter)
      const response = await apiFetch(`/reports/admin?${query}`, {
        headers: { Authorization: `Bearer ${token}` },
        signal,
      })
      const data = await readApiResponse(response)

      if (response.status === 403) {
        setAccessDenied(true)
        setReportPage(EMPTY_PAGE)
        return
      }
      if (!response.ok) throw new Error(getApiError(data, "No pudimos cargar los reportes de seguridad"))

      const normalized = normalizeReportPage(data)
      if (page > normalized.totalPages) {
        setPage(normalized.totalPages)
        return
      }
      setReportPage(normalized)
      setDrafts(Object.fromEntries(normalized.items.map((report) => [
        report.id,
        { status: report.status, note: report.moderator_note || "" },
      ])))
    } catch (loadError) {
      if (signal.aborted) return
      setError(loadError.message)
    } finally {
      if (!signal.aborted) setLoading(false)
    }
  }, [page, statusFilter, token])

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => loadReports(controller.signal), 0)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [loadAttempt, loadReports])

  function chooseFilter(nextStatus) {
    setStatusFilter(nextStatus)
    setPage(1)
  }

  function updateDraft(reportId, field, value) {
    setDrafts((current) => ({
      ...current,
      [reportId]: { ...current[reportId], [field]: value },
    }))
  }

  async function saveReview(report) {
    const draft = drafts[report.id]
    if (!draft || updatingId !== null) return
    if (["resolved", "dismissed"].includes(draft.status) && draft.note.trim().length < 3) {
      setError("Agregue una nota breve antes de cerrar el reporte.")
      return
    }

    setUpdatingId(report.id)
    setError("")

    try {
      const response = await apiFetch(`/reports/admin/${report.id}`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "X-Report-Version": String(report.version),
        },
        body: JSON.stringify({
          status: draft.status,
          moderator_note: draft.note,
        }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "No pudimos actualizar el reporte de seguridad"))
      setLoadAttempt((current) => current + 1)
    } catch (updateError) {
      setError(updateError.message)
    } finally {
      setUpdatingId(null)
    }
  }

  async function toggleSafetyHold(report) {
    const action = getSafetyHoldAction(report)
    if (!action || updatingId !== null || holdingId !== null) return

    const confirmed = window.confirm(action.held
      ? "¿Ocultar temporalmente este anuncio de las búsquedas y bloquear consultas nuevas?"
      : "¿Liberar este anuncio de la retención de seguridad?")
    if (!confirmed) return

    setHoldingId(report.id)
    setError("")
    try {
      const response = await apiFetch(`/reports/admin/${report.id}/listing-hold`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "X-Listing-Safety-Version": String(report.listing_safety_version),
        },
        body: JSON.stringify({ held: action.held }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "No pudimos actualizar la retención de seguridad"))
      setLoadAttempt((current) => current + 1)
    } catch (holdError) {
      setError(holdError.message)
    } finally {
      setHoldingId(null)
    }
  }

  if (accessDenied) {
    return (
      <main className="safety-page safety-access-denied">
        <h1>Se requiere acceso administrativo</h1>
        <p>Esta sección está disponible únicamente para administradores de seguridad autorizados.</p>
        <Link to="/">Volver a HabitaRD</Link>
      </main>
    )
  }

  return (
    <main className="safety-page">
      <header className="safety-header">
        <div>
          <p className="safety-eyebrow">Seguridad de HabitaRD</p>
          <h1>Reportes de propiedades</h1>
          <p>Revise las inquietudes usando la evidencia guardada del anuncio. Las decisiones no modifican ni eliminan propiedades automáticamente.</p>
        </div>
        <button type="button" onClick={() => setLoadAttempt((current) => current + 1)} disabled={loading}>
          {loading ? "Actualizando…" : "Actualizar"}
        </button>
      </header>

      <nav className="safety-filters" aria-label="Filtros por estado del reporte">
        <button className={statusFilter === "" ? "active" : ""} type="button" onClick={() => chooseFilter("")}>Todos <span>{reportPage.counts.all}</span></button>
        {REPORT_STATUSES.map((status) => (
          <button className={statusFilter === status ? "active" : ""} type="button" key={status} onClick={() => chooseFilter(status)}>
            {STATUS_LABELS[status]} <span>{reportPage.counts[status]}</span>
          </button>
        ))}
      </nav>

      {error && (
        <div className="safety-error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setLoadAttempt((current) => current + 1)}>Recargar reportes</button>
        </div>
      )}

      {loading && reportPage.items.length === 0 ? (
        <p className="safety-empty">Cargando reportes de seguridad…</p>
      ) : reportPage.items.length === 0 ? (
        <p className="safety-empty">No hay reportes con este estado.</p>
      ) : (
        <section className="safety-report-list" aria-label="Reportes de seguridad">
          {reportPage.items.map((report) => {
            const draft = drafts[report.id] || { status: report.status, note: report.moderator_note || "" }
            const unchanged = draft.status === report.status && draft.note.trim() === (report.moderator_note || "")
            const holdAction = getSafetyHoldAction(report)
            return (
              <article className="safety-report-card" key={report.id}>
                <div className="safety-report-topline">
                  <div>
                    <span className={`safety-status ${report.status}`}>{STATUS_LABELS[report.status]}</span>
                    <strong>Reporte #{report.id}</strong>
                    <span>{formatReportDate(report.created_at)}</span>
                  </div>
                  <span>{REPORT_REASON_LABELS[report.reason] || report.reason}</span>
                </div>

                <div className="safety-report-grid">
                  <div>
                    <span>Propiedad</span>
                    {report.property_id ? (
                      <Link to={`/properties/${report.property_id}`}>{report.listing_title} · {formatPropertyReference(report.listing_id)}</Link>
                    ) : (
                      <strong>{report.listing_title} · {formatPropertyReference(report.listing_id)} (eliminada)</strong>
                    )}
                  </div>
                  <div><span>Propietario del anuncio</span><strong>{report.listing_owner_name} · Cuenta #{report.listing_owner_id}</strong></div>
                  <div><span>Reportado por</span><strong>{report.reporter_name} · Cuenta #{report.reporter_id}</strong></div>
                  <div><span>Último revisor</span><strong>{report.reviewer_name || "Todavía no revisado"}</strong></div>
                </div>

                <div className="safety-report-details">
                  <span>Detalles del usuario</span>
                  <p>{report.details || "No se proporcionaron detalles adicionales."}</p>
                </div>

                <div className={`safety-hold-control${report.listing_on_safety_hold ? " active" : ""}`}>
                  <div>
                    <strong>{report.listing_on_safety_hold ? "Retención de seguridad activa" : "Control de seguridad del anuncio"}</strong>
                    <span>La retención oculta el anuncio y pausa consultas nuevas sin eliminarlo. El anunciante todavía puede corregir sus datos.</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleSafetyHold(report)}
                    disabled={!holdAction || updatingId !== null || holdingId !== null}
                  >
                    {holdingId === report.id ? "Actualizando…" : holdAction?.label || "Anuncio eliminado"}
                  </button>
                </div>

                <div className="safety-review-controls">
                  <label>
                    <span>Decisión</span>
                    <select value={draft.status} onChange={(event) => updateDraft(report.id, "status", event.target.value)} disabled={updatingId !== null}>
                      {getModerationStatusOptions(report.status).map((status) => (
                        <option key={status} value={status}>{STATUS_LABELS[status]}</option>
                      ))}
                    </select>
                  </label>
                  <label className="safety-review-note">
                    <span>Nota de revisión</span>
                    <textarea value={draft.note} onChange={(event) => updateDraft(report.id, "note", event.target.value)} maxLength="1000" rows="3" disabled={updatingId !== null} placeholder="Indique qué se verificó y el próximo paso, si corresponde." />
                    <small>{draft.note.length}/1000</small>
                  </label>
                  <button type="button" onClick={() => saveReview(report)} disabled={updatingId !== null || unchanged}>
                    {updatingId === report.id ? "Guardando…" : "Guardar revisión"}
                  </button>
                </div>
              </article>
            )
          })}
        </section>
      )}

      {reportPage.totalPages > 1 && (
        <nav className="safety-pagination" aria-label="Páginas de reportes de seguridad">
          <button type="button" disabled={page <= 1 || loading} onClick={() => setPage((current) => current - 1)}>Anterior</button>
          <span>Página {reportPage.page} de {reportPage.totalPages}</span>
          <button type="button" disabled={page >= reportPage.totalPages || loading} onClick={() => setPage((current) => current + 1)}>Siguiente</button>
        </nav>
      )}
    </main>
  )
}

export default SafetyReports
