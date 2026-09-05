import { useCallback, useEffect, useState } from "react"
import { Link } from "react-router-dom"

import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { normalizeMyReportPage, REPORT_REASON_LABELS } from "../utils/moderation"
import { formatPropertyReference } from "../utils/propertyReference"
import "./MySafetyReports.css"

const STATUS_CONTENT = {
  submitted: ["Recibido", "Su reporte fue registrado y está pendiente de revisión."],
  reviewing: ["En revisión", "Un administrador de seguridad está revisando la información."],
  resolved: ["Revisión completada", "El reporte fue revisado y cerrado."],
  dismissed: ["Revisión cerrada", "El reporte fue revisado y cerrado sin acciones adicionales."],
}

const EMPTY_PAGE = { items: [], total: 0, page: 1, pageSize: 20, totalPages: 1 }

function formatDate(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? "Fecha no disponible" : date.toLocaleString("es-DO")
}

function MySafetyReports() {
  const { token } = useAuth()
  const [reportPage, setReportPage] = useState(EMPTY_PAGE)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [loadAttempt, setLoadAttempt] = useState(0)

  const loadReports = useCallback(async (signal) => {
    if (!token) return
    setLoading(true)
    setError("")

    try {
      const response = await apiFetch(`/reports/mine?page=${page}&page_size=20`, {
        headers: { Authorization: `Bearer ${token}` },
        signal,
      })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "No pudimos cargar sus reportes de seguridad"))

      const normalized = normalizeMyReportPage(data)
      if (page > normalized.totalPages) {
        setPage(normalized.totalPages)
        return
      }
      setReportPage(normalized)
    } catch (loadError) {
      if (!signal.aborted) setError(loadError.message)
    } finally {
      if (!signal.aborted) setLoading(false)
    }
  }, [page, token])

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => loadReports(controller.signal), 0)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [loadAttempt, loadReports])

  return (
    <main className="my-reports-page">
      <header className="my-reports-header">
        <div>
          <p>Seguridad de HabitaRD</p>
          <h1>Mis reportes de seguridad</h1>
          <span>Consulte los reportes que ha enviado. Las notas internas y los reportes de otras personas permanecen privados.</span>
        </div>
        <button type="button" onClick={() => setLoadAttempt((current) => current + 1)} disabled={loading}>
          {loading ? "Actualizando…" : "Actualizar"}
        </button>
      </header>

      {error && (
        <div className="my-reports-error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setLoadAttempt((current) => current + 1)}>Intentar de nuevo</button>
        </div>
      )}

      {loading && reportPage.items.length === 0 ? (
        <p className="my-reports-empty">Cargando sus reportes…</p>
      ) : reportPage.items.length === 0 ? (
        <div className="my-reports-empty">
          <h2>Todavía no ha enviado reportes</h2>
          <p>Puede reportar una inquietud desde la página de cualquier propiedad que no le pertenezca.</p>
          <Link to="/">Explorar propiedades</Link>
        </div>
      ) : (
        <section className="my-reports-list" aria-label="Sus reportes de seguridad">
          {reportPage.items.map((report) => {
            const [statusLabel, statusDescription] = STATUS_CONTENT[report.status]
            return (
              <article className="my-report-card" key={report.id}>
                <div className="my-report-heading">
                  <div>
                    <span className={`my-report-status ${report.status}`}>{statusLabel}</span>
                    <strong>Reporte de seguridad #{report.id}</strong>
                  </div>
                  <span>Enviado el {formatDate(report.created_at)}</span>
                </div>

                <div className="my-report-listing">
                  <span>Propiedad</span>
                  {report.property_id ? (
                    <Link to={`/properties/${report.property_id}`}>
                      {report.listing_title} · {formatPropertyReference(report.listing_id)}
                    </Link>
                  ) : (
                    <strong>{report.listing_title} · {formatPropertyReference(report.listing_id)} (eliminada)</strong>
                  )}
                </div>

                <div className="my-report-content">
                  <div><span>Motivo</span><strong>{REPORT_REASON_LABELS[report.reason] || report.reason}</strong></div>
                  <div><span>Sus detalles</span><p>{report.details || "No proporcionó detalles adicionales."}</p></div>
                </div>

                <div className="my-report-update">
                  <strong>{statusDescription}</strong>
                  <span>Última actualización: {formatDate(report.updated_at)}</span>
                </div>
              </article>
            )
          })}
        </section>
      )}

      {reportPage.totalPages > 1 && (
        <nav className="my-reports-pagination" aria-label="Páginas de sus reportes de seguridad">
          <button type="button" disabled={page <= 1 || loading} onClick={() => setPage((current) => current - 1)}>Anterior</button>
          <span>Página {reportPage.page} de {reportPage.totalPages}</span>
          <button type="button" disabled={page >= reportPage.totalPages || loading} onClick={() => setPage((current) => current + 1)}>Siguiente</button>
        </nav>
      )}
    </main>
  )
}

export default MySafetyReports
