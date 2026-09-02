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
  submitted: "Submitted",
  reviewing: "Reviewing",
  resolved: "Resolved",
  dismissed: "Dismissed",
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
  return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleString()
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
      if (!response.ok) throw new Error(getApiError(data, "Failed to load safety reports"))

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
      setError("Add a short review note before closing a report.")
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
      if (!response.ok) throw new Error(getApiError(data, "Failed to update safety report"))
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
      ? "Temporarily remove this listing from discovery and block new inquiries?"
      : "Release this listing from safety hold?")
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
      if (!response.ok) throw new Error(getApiError(data, "Failed to update listing safety hold"))
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
        <h1>Administrator access required</h1>
        <p>This moderation queue is available only to explicitly configured safety administrators.</p>
        <Link to="/">Return to marketplace</Link>
      </main>
    )
  }

  return (
    <main className="safety-page">
      <header className="safety-header">
        <div>
          <p className="safety-eyebrow">Marketplace safety</p>
          <h1>Listing Reports</h1>
          <p>Review buyer concerns using the saved listing evidence. Decisions do not automatically edit or remove listings.</p>
        </div>
        <button type="button" onClick={() => setLoadAttempt((current) => current + 1)} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      <nav className="safety-filters" aria-label="Report status filters">
        <button className={statusFilter === "" ? "active" : ""} type="button" onClick={() => chooseFilter("")}>All <span>{reportPage.counts.all}</span></button>
        {REPORT_STATUSES.map((status) => (
          <button className={statusFilter === status ? "active" : ""} type="button" key={status} onClick={() => chooseFilter(status)}>
            {STATUS_LABELS[status]} <span>{reportPage.counts[status]}</span>
          </button>
        ))}
      </nav>

      {error && (
        <div className="safety-error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setLoadAttempt((current) => current + 1)}>Reload queue</button>
        </div>
      )}

      {loading && reportPage.items.length === 0 ? (
        <p className="safety-empty">Loading safety reports…</p>
      ) : reportPage.items.length === 0 ? (
        <p className="safety-empty">No reports match this status.</p>
      ) : (
        <section className="safety-report-list" aria-label="Safety reports">
          {reportPage.items.map((report) => {
            const draft = drafts[report.id] || { status: report.status, note: report.moderator_note || "" }
            const unchanged = draft.status === report.status && draft.note.trim() === (report.moderator_note || "")
            const holdAction = getSafetyHoldAction(report)
            return (
              <article className="safety-report-card" key={report.id}>
                <div className="safety-report-topline">
                  <div>
                    <span className={`safety-status ${report.status}`}>{STATUS_LABELS[report.status]}</span>
                    <strong>Report #{report.id}</strong>
                    <span>{formatReportDate(report.created_at)}</span>
                  </div>
                  <span>{REPORT_REASON_LABELS[report.reason] || report.reason}</span>
                </div>

                <div className="safety-report-grid">
                  <div>
                    <span>Listing</span>
                    {report.property_id ? (
                      <Link to={`/properties/${report.property_id}`}>{report.listing_title} · {formatPropertyReference(report.listing_id)}</Link>
                    ) : (
                      <strong>{report.listing_title} · {formatPropertyReference(report.listing_id)} (removed)</strong>
                    )}
                  </div>
                  <div><span>Listing owner</span><strong>{report.listing_owner_name} · Account #{report.listing_owner_id}</strong></div>
                  <div><span>Reported by</span><strong>{report.reporter_name} · Account #{report.reporter_id}</strong></div>
                  <div><span>Last reviewer</span><strong>{report.reviewer_name || "Not reviewed yet"}</strong></div>
                </div>

                <div className="safety-report-details">
                  <span>Buyer details</span>
                  <p>{report.details || "No additional details were provided."}</p>
                </div>

                <div className={`safety-hold-control${report.listing_on_safety_hold ? " active" : ""}`}>
                  <div>
                    <strong>{report.listing_on_safety_hold ? "Safety hold active" : "Listing safety control"}</strong>
                    <span>A hold hides the listing from discovery and pauses new inquiries without deleting it. The seller can still correct its details.</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => toggleSafetyHold(report)}
                    disabled={!holdAction || updatingId !== null || holdingId !== null}
                  >
                    {holdingId === report.id ? "Updating…" : holdAction?.label || "Listing removed"}
                  </button>
                </div>

                <div className="safety-review-controls">
                  <label>
                    <span>Decision</span>
                    <select value={draft.status} onChange={(event) => updateDraft(report.id, "status", event.target.value)} disabled={updatingId !== null}>
                      {getModerationStatusOptions(report.status).map((status) => (
                        <option key={status} value={status}>{STATUS_LABELS[status]}</option>
                      ))}
                    </select>
                  </label>
                  <label className="safety-review-note">
                    <span>Review note</span>
                    <textarea value={draft.note} onChange={(event) => updateDraft(report.id, "note", event.target.value)} maxLength="1000" rows="3" disabled={updatingId !== null} placeholder="Record what was checked and any next step." />
                    <small>{draft.note.length}/1000</small>
                  </label>
                  <button type="button" onClick={() => saveReview(report)} disabled={updatingId !== null || unchanged}>
                    {updatingId === report.id ? "Saving…" : "Save Review"}
                  </button>
                </div>
              </article>
            )
          })}
        </section>
      )}

      {reportPage.totalPages > 1 && (
        <nav className="safety-pagination" aria-label="Safety report pages">
          <button type="button" disabled={page <= 1 || loading} onClick={() => setPage((current) => current - 1)}>Previous</button>
          <span>Page {reportPage.page} of {reportPage.totalPages}</span>
          <button type="button" disabled={page >= reportPage.totalPages || loading} onClick={() => setPage((current) => current + 1)}>Next</button>
        </nav>
      )}
    </main>
  )
}

export default SafetyReports
