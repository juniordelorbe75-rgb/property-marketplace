import { useCallback, useEffect, useRef, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import "./Inquiry.css"
import { apiFetch } from "../utils/apiFetch"
import { formatPropertyReference, normalizePropertyReference } from "../utils/propertyReference"
import { notifyInquiriesChanged } from "../utils/inquiryEvents"
import { buildInquiryPageUrl, EMPTY_INQUIRY_COUNTS, normalizeInquiryPage } from "../utils/inquiryPage"

const INQUIRY_STATUSES = ["pending", "accepted", "rejected", "cancelled"]
const INQUIRIES_PER_PAGE = 6

function titleCase(value) {
  return value.charAt(0).toUpperCase() + value.slice(1)
}

function InquiryFilters({ counts, value, onChange }) {
  const filters = ["all", ...INQUIRY_STATUSES]

  return (
    <div className="inquiry-filters" aria-label="Filter inquiries by status">
      {filters.map((status) => {
        return (
          <button
            key={status}
            type="button"
            className={value === status ? "active" : ""}
            aria-pressed={value === status}
            onClick={() => onChange(status)}
          >
            {titleCase(status)} <span>{counts[status] || 0}</span>
          </button>
        )
      })}
    </div>
  )
}

function InquiryPagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null
  return (
    <nav className="inquiry-pagination" aria-label="Inquiry pages">
      <button type="button" disabled={page <= 1} onClick={() => onChange(page - 1)}>Previous</button>
      <span aria-current="page">Page {page} of {totalPages}</span>
      <button type="button" disabled={page >= totalPages} onClick={() => onChange(page + 1)}>Next</button>
    </nav>
  )
}

function formatInquiryDate(value) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return "Unknown"
  }

  return new Intl.DateTimeFormat(undefined, {
    year: "numeric",
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  }).format(date)
}

function InquiryConversation({ inquiry, viewerRole }) {
  const messages = Array.isArray(inquiry.conversation_messages)
    ? inquiry.conversation_messages
    : []

  return (
    <div className="inquiry-conversation" aria-label="Conversation">
      {messages.map((message, index) => {
        const isMine = message.sender_role === viewerRole
        return (
          <div
            className={`inquiry-message ${isMine ? "mine" : "theirs"}`}
            key={message.id ?? `${message.sender_role}-${index}`}
          >
            <div className="inquiry-message-heading">
              <strong>{isMine ? "You" : message.sender_name}</strong>
              <span>{formatInquiryDate(message.created_at)}</span>
            </div>
            <p>{message.body}</p>
          </div>
        )
      })}
    </div>
  )
}

function InquiryReplyComposer({ inquiry, value, sending, notice, onChange, onSend }) {
  const canMessage = ["pending", "accepted"].includes(inquiry.status)
  if (!canMessage) {
    return <p className="inquiry-closed-message">This conversation is closed.</p>
  }

  return (
    <form className="inquiry-reply-form" onSubmit={(event) => { event.preventDefault(); onSend() }}>
      <label htmlFor={`inquiry-reply-${inquiry.id}`}>Reply in this conversation</label>
      <textarea
        id={`inquiry-reply-${inquiry.id}`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Write your message..."
        rows="3"
        maxLength="1000"
        disabled={sending}
      />
      <div className="inquiry-reply-footer">
        <span>{value.length}/1000</span>
        <button className="reply-button" type="submit" disabled={sending || !value.trim()}>
          {sending ? "Sending..." : "Send reply"}
        </button>
      </div>
      {notice && <p className="inquiry-reply-notice" role="status">{notice}</p>}
    </form>
  )
}

function Inquiries() {
  const { logout } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [sentInquiries, setSentInquiries] = useState([])
  const [receivedInquiries, setReceivedInquiries] = useState([])
  const [sentFilter, setSentFilter] = useState("all")
  const [receivedFilter, setReceivedFilter] = useState("all")
  const [sentPage, setSentPage] = useState(1)
  const [receivedPage, setReceivedPage] = useState(1)
  const [sentMeta, setSentMeta] = useState({ total: 0, totalPages: 1, counts: EMPTY_INQUIRY_COUNTS })
  const [receivedMeta, setReceivedMeta] = useState({ total: 0, totalPages: 1, counts: EMPTY_INQUIRY_COUNTS })

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [loadError, setLoadError] = useState("")

  const [updatingInquiry, setUpdatingInquiry] = useState(null)
  const [cancellingInquiry, setCancellingInquiry] = useState(null)

  const [replyMessages, setReplyMessages] = useState({})
  const [replyKeys, setReplyKeys] = useState({})
  const [replyNotices, setReplyNotices] = useState({})
  const [replyingInquiry, setReplyingInquiry] = useState(null)
  const loadControllerRef = useRef(null)

  const propertyReference = normalizePropertyReference(searchParams.get("property"))

  function clearPropertyFilter() {
    const nextParams = new URLSearchParams(searchParams)
    nextParams.delete("property")
    setSearchParams(nextParams, { replace: true })
    setSentPage(1)
    setReceivedPage(1)
  }

  const fetchInquiries = useCallback(async (options = {}) => {
    const background = options?.background === true
    const token = localStorage.getItem("access_token")

    if (!token) {
      setLoadError("Please log in to view your inquiries.")
      setLoading(false)
      return
    }

    loadControllerRef.current?.abort()
    const controller = new AbortController()
    loadControllerRef.current = controller
    if (!background) setLoading(true)
    setLoadError("")

    try {
      const sentUrl = buildInquiryPageUrl("sent", {
        page: sentPage,
        pageSize: INQUIRIES_PER_PAGE,
        status: sentFilter,
        propertyReference,
      })
      const receivedUrl = buildInquiryPageUrl("received", {
        page: receivedPage,
        pageSize: INQUIRIES_PER_PAGE,
        status: receivedFilter,
        propertyReference,
      })
      const [sentResponse, receivedResponse] =
        await Promise.all([
          apiFetch(
            sentUrl,
            {
              headers: {
                Authorization: `Bearer ${token}`,
              },
              signal: controller.signal,
            }
          ),

          apiFetch(
            receivedUrl,
            {
              headers: {
                Authorization: `Bearer ${token}`,
              },
              signal: controller.signal,
            }
          ),
        ])

      const sentData = await readApiResponse(sentResponse)
      const receivedData =
        await readApiResponse(receivedResponse)

      if (
        sentResponse.status === 401
        || receivedResponse.status === 401
      ) {
        logout()
        return
      }

      if (!sentResponse.ok) {
        throw new Error(
          sentData.detail ||
            "Failed to load sent inquiries"
        )
      }

      if (!receivedResponse.ok) {
        throw new Error(
          receivedData.detail ||
            "Failed to load received inquiries"
        )
      }

      const normalizedSent = normalizeInquiryPage(sentData)
      const normalizedReceived = normalizeInquiryPage(receivedData)
      setSentInquiries(normalizedSent.items)
      setReceivedInquiries(normalizedReceived.items)
      setSentMeta(normalizedSent)
      setReceivedMeta(normalizedReceived)
      if (normalizedSent.page !== sentPage) setSentPage(normalizedSent.page)
      if (normalizedReceived.page !== receivedPage) setReceivedPage(normalizedReceived.page)

    } catch (error) {
      if (error.name === "AbortError") return

      console.error("Inquiries error:", error)
      setLoadError(error.message)

    } finally {
      if (loadControllerRef.current === controller) {
        loadControllerRef.current = null
        setLoading(false)
      }
    }
  }, [logout, propertyReference, receivedFilter, receivedPage, sentFilter, sentPage])

  useEffect(() => {
    const loadTimer = window.setTimeout(fetchInquiries, 0)

    return () => {
      window.clearTimeout(loadTimer)
      loadControllerRef.current?.abort()
    }
  }, [fetchInquiries])

  async function updateInquiryStatus(
    inquiryId,
    status
  ) {
    const token =
      localStorage.getItem("access_token")

    if (!token) {
      setError("Please log in.")
      return
    }

    setUpdatingInquiry(inquiryId)
    setError("")

    try {
      const response = await apiFetch(
        `/inquiries/${inquiryId}/status`,
        {
          method: "PATCH",

          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },

          body: JSON.stringify({
            status: status,
          }),
        }
      )

      const data = await readApiResponse(response)

      if (response.status === 401) {
        logout()
        return
      }

      if (!response.ok) {
        throw new Error(
          getApiError(data, "Failed to update inquiry status")
        )
      }

      notifyInquiriesChanged()
      await fetchInquiries({ background: true })

    } catch (error) {
      console.error(
        "Update inquiry error:",
        error
      )

      setError(error.message)

    } finally {
      setUpdatingInquiry(null)
    }
  }

  async function sendInquiryMessage(inquiryId) {
    const token =
      localStorage.getItem("access_token")

    if (!token) {
      setError("Please log in.")
      return
    }

    const replyMessage =
      replyMessages[inquiryId]?.trim()

    if (!replyMessage) {
      setError("Please enter a reply.")
      return
    }

    setReplyingInquiry(inquiryId)
    setError("")
    setReplyNotices((current) => ({ ...current, [inquiryId]: "" }))
    const creationKey = replyKeys[inquiryId] || crypto.randomUUID()
    if (!replyKeys[inquiryId]) {
      setReplyKeys((current) => ({ ...current, [inquiryId]: creationKey }))
    }

    try {
      const response = await apiFetch(
        `/inquiries/${inquiryId}/messages`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
            "Idempotency-Key": creationKey,
          },

          body: JSON.stringify({
            message: replyMessage,
          }),
        }
      )

      const data = await readApiResponse(response)

      if (response.status === 401) {
        logout()
        return
      }

      if (!response.ok) {
        throw new Error(
          getApiError(data, "Failed to send reply")
        )
      }

      setReplyMessages(
        (currentMessages) => ({
          ...currentMessages,
          [inquiryId]: "",
        })
      )

    } catch (error) {
      console.error(
        "Reply error:",
        error
      )

      setError(error.message)

    } finally {
      setReplyingInquiry(null)
    }
  }

  async function cancelInquiry(inquiryId) {
    if (!window.confirm("Cancel this inquiry? This cannot be undone.")) {
      return
    }

    const token = localStorage.getItem("access_token")

    if (!token) {
      setError("Please log in.")
      return
    }

    setCancellingInquiry(inquiryId)
    setError("")

    try {
      const response = await apiFetch(
        `/inquiries/${inquiryId}/cancel`,
        {
          method: "PATCH",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )
      setReplyKeys((current) => ({ ...current, [inquiryId]: crypto.randomUUID() }))
      setReplyNotices((current) => ({ ...current, [inquiryId]: "Reply sent." }))
      await fetchInquiries({ background: true })
      await fetchInquiries({ background: true })
      const data = await readApiResponse(response)

      if (response.status === 401) {
        logout()
        return
      }

      if (!response.ok) {
        throw new Error(
          getApiError(data, "Failed to cancel inquiry")
        )
      }

      await fetchInquiries({ background: true })
    } catch (error) {
      console.error("Cancel inquiry error:", error)
      setError(error.message)
    } finally {
      setCancellingInquiry(null)
    }
  }

  if (loading) {
    return (
      <div className="inquiries-page">
        <p className="inquiry-loading" role="status">Loading inquiries...</p>
      </div>
    )
  }

  return (
    <div className="inquiries-page">

      <div className="inquiries-header">

        <h1>My Inquiries</h1>

        <p>
          Manage your property inquiries.
        </p>

      </div>

      {loadError && (
        <div className="inquiry-load-error" role="alert">
          <p>{loadError}</p>
          <button type="button" onClick={fetchInquiries}>Try again</button>
        </div>
      )}

      {error && (
        <p className="inquiry-error" role="alert">{error}</p>
      )}

      {propertyReference && (
        <div className="inquiry-property-filter" role="status">
          <span>Showing conversations for <strong>{propertyReference}</strong>.</span>
          <button type="button" onClick={clearPropertyFilter}>Show all inquiries</button>
        </div>
      )}

      {/* SENT INQUIRIES */}

      {!loadError && <section className="inquiries-section">

        <h2>Sent Inquiries</h2>

        {sentMeta.counts.all === 0 ? (

          <p>
            You haven't sent any inquiries yet.
          </p>

        ) : (

          <>

          <InquiryFilters
            counts={sentMeta.counts}
            value={sentFilter}
            onChange={(status) => { setSentFilter(status); setSentPage(1) }}
          />

          {sentInquiries.length === 0 ? (
            <p className="inquiry-empty-filter">
              No {sentFilter} sent inquiries.
            </p>
          ) : (

          <div className="inquiries-grid">

            {sentInquiries.map(
              (inquiry) => (

                <div
                  className="inquiry-card"
                  key={inquiry.id}
                >

                  <h3>
                    Inquiry #{inquiry.id}
                  </h3>

                  <p>
                    To: {inquiry.seller_name}
                  </p>

                  <p>
                    Property:{" "}
                    {inquiry.property_title}
                  </p>

                  <p className="inquiry-reference">
                    Reference: {formatPropertyReference(inquiry.property_id)}
                  </p>

                  <p className="inquiry-date">
                    Sent {formatInquiryDate(inquiry.created_at)}
                  </p>

                  <p className="inquiry-date">
                    Last activity {formatInquiryDate(inquiry.updated_at)}
                  </p>

                  <p className="inquiry-status">

                    Status:{" "}

                    <span
                      className={
                        inquiry.status
                      }
                    >
                      {inquiry.status}
                    </span>

                  </p>

                  <InquiryConversation inquiry={inquiry} viewerRole="buyer" />

                  <Link
                    className="inquiry-link"
                    to={`/properties/${inquiry.property_id}`}
                  >
                    View Property
                  </Link>

                  {inquiry.status === "pending" && (
                    <div className="inquiry-actions">
                      <button
                        className="cancel-button"
                        onClick={() => cancelInquiry(inquiry.id)}
                        disabled={cancellingInquiry === inquiry.id}
                      >
                        {cancellingInquiry === inquiry.id
                          ? "Cancelling..."
                          : "Cancel Inquiry"}
                      </button>
                    </div>
                  )}

                  <InquiryReplyComposer
                    inquiry={inquiry}
                    value={replyMessages[inquiry.id] || ""}
                    sending={replyingInquiry === inquiry.id}
                    notice={replyNotices[inquiry.id] || ""}
                    onChange={(message) => {
                      setReplyMessages((current) => ({ ...current, [inquiry.id]: message }))
                      setReplyNotices((current) => ({ ...current, [inquiry.id]: "" }))
                    }}
                    onSend={() => sendInquiryMessage(inquiry.id)}
                  />

                </div>

              )
            )}

          </div>

          )}

          <InquiryPagination page={sentPage} totalPages={sentMeta.totalPages} onChange={setSentPage} />

          </>

        )}

      </section>}

      {/* RECEIVED INQUIRIES */}

      {!loadError && <section className="inquiries-section">

        <h2>Received Inquiries</h2>

        {receivedMeta.counts.all === 0 ? (

          <p>
            You haven't received any inquiries yet.
          </p>

        ) : (

          <>

          <InquiryFilters
            counts={receivedMeta.counts}
            value={receivedFilter}
            onChange={(status) => { setReceivedFilter(status); setReceivedPage(1) }}
          />

          {receivedInquiries.length === 0 ? (
            <p className="inquiry-empty-filter">
              No {receivedFilter} received inquiries.
            </p>
          ) : (

          <div className="inquiries-grid">

            {receivedInquiries.map(
              (inquiry) => (

                <div
                  className="inquiry-card"
                  key={inquiry.id}
                >

                  <h3>
                    Inquiry #{inquiry.id}
                  </h3>

                  <p>
                    From: {inquiry.buyer_name}
                  </p>

                  <p>
                    Property:{" "}
                    {inquiry.property_title}
                  </p>

                  <p className="inquiry-reference">
                    Reference: {formatPropertyReference(inquiry.property_id)}
                  </p>

                  <p className="inquiry-date">
                    Received {formatInquiryDate(inquiry.created_at)}
                  </p>

                  <p className="inquiry-date">
                    Last activity {formatInquiryDate(inquiry.updated_at)}
                  </p>

                  <p className="inquiry-status">

                    Status:{" "}

                    <span
                      className={
                        inquiry.status
                      }
                    >
                      {inquiry.status}
                    </span>

                  </p>

                  <InquiryConversation inquiry={inquiry} viewerRole="seller" />

                  <Link
                    className="inquiry-link"
                    to={`/properties/${inquiry.property_id}`}
                  >
                    View Property
                  </Link>

                  {/* ACCEPT / REJECT */}

                  {inquiry.status ===
                    "pending" && (

                    <div className="inquiry-actions">

                      <button
                        className="accept-button"
                        onClick={() =>
                          updateInquiryStatus(
                            inquiry.id,
                            "accepted"
                          )
                        }
                        disabled={
                          updatingInquiry ===
                          inquiry.id
                        }
                      >
                        {updatingInquiry ===
                        inquiry.id
                          ? "Updating..."
                          : "Accept"}
                      </button>

                      <button
                        className="reject-button"
                        onClick={() =>
                          updateInquiryStatus(
                            inquiry.id,
                            "rejected"
                          )
                        }
                        disabled={
                          updatingInquiry ===
                          inquiry.id
                        }
                      >
                        {updatingInquiry ===
                        inquiry.id
                          ? "Updating..."
                          : "Reject"}
                      </button>

                    </div>

                  )}

                  <InquiryReplyComposer
                    inquiry={inquiry}
                    value={replyMessages[inquiry.id] || ""}
                    sending={replyingInquiry === inquiry.id}
                    notice={replyNotices[inquiry.id] || ""}
                    onChange={(message) => {
                      setReplyMessages((current) => ({ ...current, [inquiry.id]: message }))
                      setReplyNotices((current) => ({ ...current, [inquiry.id]: "" }))
                    }}
                    onSend={() => sendInquiryMessage(inquiry.id)}
                  />

                </div>

              )
            )}

          </div>

          )}

          <InquiryPagination page={receivedPage} totalPages={receivedMeta.totalPages} onChange={setReceivedPage} />

          </>

        )}

      </section>}

    </div>
  )
}

export default Inquiries
