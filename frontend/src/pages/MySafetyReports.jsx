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
  submitted: ["Received", "Your report was recorded and is waiting for review."],
  reviewing: ["Being reviewed", "A safety administrator is reviewing the information."],
  resolved: ["Review complete", "The report was reviewed and closed."],
  dismissed: ["Review closed", "The report was reviewed and closed without further action."],
}

const EMPTY_PAGE = { items: [], total: 0, page: 1, pageSize: 20, totalPages: 1 }

function formatDate(value) {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? "Date unavailable" : date.toLocaleString()
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
      if (!response.ok) throw new Error(getApiError(data, "Failed to load your safety reports"))

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
          <p>Marketplace safety</p>
          <h1>My Safety Reports</h1>
          <span>Track reports you submitted. Internal review notes and other users’ reports remain private.</span>
        </div>
        <button type="button" onClick={() => setLoadAttempt((current) => current + 1)} disabled={loading}>
          {loading ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      {error && (
        <div className="my-reports-error" role="alert">
          <span>{error}</span>
          <button type="button" onClick={() => setLoadAttempt((current) => current + 1)}>Try again</button>
        </div>
      )}

      {loading && reportPage.items.length === 0 ? (
        <p className="my-reports-empty">Loading your reports…</p>
      ) : reportPage.items.length === 0 ? (
        <div className="my-reports-empty">
          <h2>No safety reports yet</h2>
          <p>You can report a concern from any property page you do not own.</p>
          <Link to="/">Explore properties</Link>
        </div>
      ) : (
        <section className="my-reports-list" aria-label="Your safety reports">
          {reportPage.items.map((report) => {
            const [statusLabel, statusDescription] = STATUS_CONTENT[report.status]
            return (
              <article className="my-report-card" key={report.id}>
                <div className="my-report-heading">
                  <div>
                    <span className={`my-report-status ${report.status}`}>{statusLabel}</span>
                    <strong>Safety report #{report.id}</strong>
                  </div>
                  <span>Submitted {formatDate(report.created_at)}</span>
                </div>

                <div className="my-report-listing">
                  <span>Listing</span>
                  {report.property_id ? (
                    <Link to={`/properties/${report.property_id}`}>
                      {report.listing_title} · {formatPropertyReference(report.listing_id)}
                    </Link>
                  ) : (
                    <strong>{report.listing_title} · {formatPropertyReference(report.listing_id)} (removed)</strong>
                  )}
                </div>

                <div className="my-report-content">
                  <div><span>Reason</span><strong>{REPORT_REASON_LABELS[report.reason] || report.reason}</strong></div>
                  <div><span>Your details</span><p>{report.details || "No additional details provided."}</p></div>
                </div>

                <div className="my-report-update">
                  <strong>{statusDescription}</strong>
                  <span>Last updated {formatDate(report.updated_at)}</span>
                </div>
              </article>
            )
          })}
        </section>
      )}

      {reportPage.totalPages > 1 && (
        <nav className="my-reports-pagination" aria-label="Your safety report pages">
          <button type="button" disabled={page <= 1 || loading} onClick={() => setPage((current) => current - 1)}>Previous</button>
          <span>Page {reportPage.page} of {reportPage.totalPages}</span>
          <button type="button" disabled={page >= reportPage.totalPages || loading} onClick={() => setPage((current) => current + 1)}>Next</button>
        </nav>
      )}
    </main>
  )
}

export default MySafetyReports
