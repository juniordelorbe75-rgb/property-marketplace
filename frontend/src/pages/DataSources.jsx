import { useCallback, useEffect, useMemo, useState } from "react"
import { Link } from "react-router-dom"

import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { getSourceHealth, normalizeDataSources } from "../utils/dataSources"
import "./DataSources.css"

const EVENT_LABELS = {
  feed_imported: "Inventario importado",
  source_approved: "Permiso aprobado",
  source_revoked: "Permiso revocado",
  listings_unpublished: "Inventario retirado",
}

function formatDate(value) {
  if (!value) return "No disponible"
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? "No disponible" : date.toLocaleString("es-DO", { dateStyle: "medium", timeStyle: "short" })
}

function DataSources() {
  const { token } = useAuth()
  const [sources, setSources] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [accessDenied, setAccessDenied] = useState(false)
  const [attempt, setAttempt] = useState(0)

  const loadSources = useCallback(async (signal) => {
    setLoading(true)
    setError("")
    setAccessDenied(false)
    try {
      const response = await apiFetch("/catalog/admin/sources", {
        headers: { Authorization: `Bearer ${token}` },
        signal,
      })
      const data = await readApiResponse(response)
      if (response.status === 403) {
        setAccessDenied(true)
        setSources([])
        return
      }
      if (!response.ok) throw new Error(getApiError(data, "No pudimos cargar las fuentes de datos"))
      setSources(normalizeDataSources(data))
    } catch (loadError) {
      if (!signal.aborted) setError(loadError.message)
    } finally {
      if (!signal.aborted) setLoading(false)
    }
  }, [token])

  useEffect(() => {
    const controller = new AbortController()
    const timer = window.setTimeout(() => loadSources(controller.signal), 0)
    return () => {
      window.clearTimeout(timer)
      controller.abort()
    }
  }, [attempt, loadSources])

  const totals = useMemo(() => sources.reduce((summary, source) => {
    const health = getSourceHealth(source)
    summary.inventory += source.total_listings
    summary.public += source.public_listings
    if (health.key === "healthy") summary.ready += 1
    if (["permission", "expired"].includes(health.key)) summary.permission += 1
    return summary
  }, { inventory: 0, public: 0, ready: 0, permission: 0 }), [sources])

  if (accessDenied) return (
    <main className="sources-page sources-access-denied">
      <h1>Se requiere acceso administrativo</h1>
      <p>La supervisión de fuentes está reservada para administradores autorizados.</p>
      <Link to="/">Volver a HabitaRD</Link>
    </main>
  )

  return (
    <main className="sources-page">
      <header className="sources-header">
        <div>
          <p className="sources-eyebrow">Control de publicación</p>
          <h1>Fuentes de datos autorizadas</h1>
          <p>Confirme permisos, vigencia e inventario antes de mostrar propiedades de aliados en HabitaRD.</p>
        </div>
        <button type="button" onClick={() => setAttempt((value) => value + 1)} disabled={loading}>{loading ? "Actualizando…" : "Actualizar"}</button>
      </header>

      <section className="sources-summary" aria-label="Resumen de fuentes">
        <article><span>Fuentes listas</span><strong>{totals.ready}</strong></article>
        <article><span>Requieren permiso</span><strong>{totals.permission}</strong></article>
        <article><span>Inventario recibido</span><strong>{totals.inventory}</strong></article>
        <article><span>Visible al público</span><strong>{totals.public}</strong></article>
      </section>

      {error && <div className="sources-error" role="alert"><span>{error}</span><button type="button" onClick={() => setAttempt((value) => value + 1)}>Intentar de nuevo</button></div>}
      {loading && sources.length === 0 ? <p className="sources-empty">Cargando fuentes autorizadas…</p> : sources.length === 0 ? (
        <div className="sources-empty"><strong>Todavía no hay fuentes registradas.</strong><span>Registre un proveedor únicamente después de confirmar sus condiciones de licencia y contacto oficial.</span></div>
      ) : (
        <section className="sources-list" aria-label="Fuentes de propiedades">
          {sources.map((source) => {
            const health = getSourceHealth(source)
            return (
              <article className="source-card" key={source.id}>
                <div className="source-card-heading">
                  <div><span className={`source-health ${health.key}`}>{health.label}</span><h2>{source.name}</h2><p>{source.attribution}</p></div>
                  <div className="source-inventory"><strong>{source.public_listings}</strong><span>de {source.total_listings} visibles</span></div>
                </div>
                <p className="source-health-detail">{health.detail}</p>
                <dl className="source-details">
                  <div><dt>Licencia</dt><dd><a href={source.license_url} target="_blank" rel="noopener noreferrer">{source.license_name}<span className="sr-only"> (abre en una pestaña nueva)</span></a></dd></div>
                  <div><dt>Permiso de republicación</dt><dd>{source.permission_document_url ? <a href={source.permission_document_url} target="_blank" rel="noopener noreferrer">Revisar evidencia<span className="sr-only"> (abre en una pestaña nueva)</span></a> : "No registrado"}</dd></div>
                  <div><dt>Vigencia del permiso</dt><dd>{source.permission_expires_at ? `Hasta ${formatDate(source.permission_expires_at)}` : source.approved ? "Sin vencimiento registrado" : "No aprobada"}</dd></div>
                  <div><dt>Última importación</dt><dd>{formatDate(source.last_retrieved_at)}</dd></div>
                  <div><dt>Último evento</dt><dd>{source.latest_event_type ? EVENT_LABELS[source.latest_event_type] || "Actividad registrada" : "Sin actividad"}{source.latest_event_at ? ` · ${formatDate(source.latest_event_at)}` : ""}</dd></div>
                  <div><dt>Límite de actualización</dt><dd>{source.stale_after_hours} horas</dd></div>
                </dl>
              </article>
            )
          })}
        </section>
      )}
    </main>
  )
}

export default DataSources
