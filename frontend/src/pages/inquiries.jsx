import { useCallback, useEffect, useRef, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import "./inquiry.css"
import { apiFetch } from "../utils/apiFetch"
import { formatPropertyReference, normalizePropertyReference } from "../utils/propertyReference"
import { notifyInquiriesChanged } from "../utils/inquiryEvents"
import {
  buildInquiryPageUrl,
  buildInquiryReadReceipts,
  EMPTY_INQUIRY_COUNTS,
  normalizeInquiryPage,
} from "../utils/inquiryPage"
import { getDraftOwnerId } from "../utils/listingDraft"
import { readInquiryDrafts, saveInquiryDrafts } from "../utils/inquiryDrafts"

const INQUIRY_STATUSES = ["pending", "accepted", "rejected", "cancelled"]
const INQUIRIES_PER_PAGE = 6

function inquiryStatusLabel(value, plural = true) {
  const labels = plural
    ? { all: "Todas", pending: "Pendientes", accepted: "Aceptadas", rejected: "Rechazadas", cancelled: "Canceladas" }
    : { pending: "Pendiente", accepted: "Aceptada", rejected: "Rechazada", cancelled: "Cancelada" }
  return labels[value] || value
}

function InquiryFilters({ counts, value, onChange }) {
  const filters = ["all", ...INQUIRY_STATUSES]

  return (
    <div className="inquiry-filters" aria-label="Filtrar consultas por estado">
      {filters.map((status) => {
        return (
          <button
            key={status}
            type="button"
            className={value === status ? "active" : ""}
            aria-pressed={value === status}
            onClick={() => onChange(status)}
          >
            {inquiryStatusLabel(status)} <span>{counts[status] || 0}</span>
          </button>
        )
      })}
    </div>
  )
}

function InquiryPagination({ page, totalPages, onChange }) {
  if (totalPages <= 1) return null
  return (
    <nav className="inquiry-pagination" aria-label="Páginas de consultas">
      <button type="button" disabled={page <= 1} onClick={() => onChange(page - 1)}>Anterior</button>
      <span aria-current="page">Página {page} de {totalPages}</span>
      <button type="button" disabled={page >= totalPages} onClick={() => onChange(page + 1)}>Siguiente</button>
    </nav>
  )
}

function formatInquiryDate(value) {
  const date = new Date(value)

  if (Number.isNaN(date.getTime())) {
    return "Fecha desconocida"
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
    <div className="inquiry-conversation" aria-label="Conversación">
      {messages.map((message, index) => {
        const isMine = message.sender_role === viewerRole
        return (
          <div
            className={`inquiry-message ${isMine ? "mine" : "theirs"}`}
            key={message.id ?? `${message.sender_role}-${index}`}
          >
            <div className="inquiry-message-heading">
              <strong>{isMine ? "Usted" : message.sender_name}</strong>
              <span>{formatInquiryDate(message.created_at)}</span>
            </div>
            <p>{message.body}</p>
          </div>
        )
      })}
    </div>
  )
}

function getConversationPreview(inquiry, viewerRole) {
  const messages = Array.isArray(inquiry.conversation_messages)
    ? inquiry.conversation_messages
    : []
  const latest = messages.at(-1)
  if (!latest) return { sender: "Sin mensajes", body: "Abra esta consulta para ver sus detalles." }
  return {
    sender: latest.sender_role === viewerRole ? "Usted" : latest.sender_name,
    body: latest.body,
  }
}

function InquiryCard({
  inquiry,
  viewerRole,
  direction,
  expanded,
  busy,
  cancelling,
  replyValue,
  replyNotice,
  replying,
  onToggle,
  onStatusChange,
  onCancel,
  onReplyChange,
  onReply,
}) {
  const contactName = direction === "sent" ? inquiry.seller_name : inquiry.buyer_name
  const preview = getConversationPreview(inquiry, viewerRole)
  const conversationId = `inquiry-conversation-${inquiry.id}`

  return (
    <article className={`inquiry-card${inquiry.unread_count > 0 ? " has-unread" : ""}`}>
      <button
        type="button"
        className="inquiry-preview-button"
        onClick={onToggle}
        aria-expanded={expanded}
        aria-controls={conversationId}
      >
        <span className="inquiry-avatar" aria-hidden="true">{contactName?.trim()?.charAt(0)?.toUpperCase() || "?"}</span>
        <span className="inquiry-preview-content">
          <span className="inquiry-preview-heading">
            <strong>{contactName || "Miembro de HabitaRD"}</strong>
            <time>{formatInquiryDate(inquiry.updated_at)}</time>
          </span>
          <span className="inquiry-property-name">{inquiry.property_title}</span>
          <span className="inquiry-message-preview"><b>{preview.sender}:</b> {preview.body}</span>
        </span>
        <span className="inquiry-preview-aside">
          {inquiry.unread_count > 0 && <span className="inquiry-unread-count">{inquiry.unread_count} {inquiry.unread_count === 1 ? "nuevo" : "nuevos"}</span>}
          <span className={`inquiry-status-pill ${inquiry.status}`}>{inquiryStatusLabel(inquiry.status, false)}</span>
          <span className="inquiry-chevron" aria-hidden="true">⌄</span>
        </span>
      </button>

      {expanded && (
        <div className="inquiry-details" id={conversationId}>
          <div className="inquiry-details-meta">
            <span>Consulta #{inquiry.id}</span>
            <span>{formatPropertyReference(inquiry.property_id)}</span>
            <span>Iniciada el {formatInquiryDate(inquiry.created_at)}</span>
          </div>

          <InquiryConversation inquiry={inquiry} viewerRole={viewerRole} />

          <div className="inquiry-detail-links">
            <Link className="inquiry-link" to={`/properties/${inquiry.property_id}`}>Ver propiedad</Link>
          </div>

          {direction === "sent" && inquiry.status === "pending" && (
            <div className="inquiry-actions">
              <button className="cancel-button" onClick={onCancel} disabled={cancelling}>
                {cancelling ? "Cancelando..." : "Cancelar consulta"}
              </button>
            </div>
          )}

          {direction === "received" && inquiry.status === "pending" && (
            <div className="inquiry-actions">
              <button className="accept-button" onClick={() => onStatusChange("accepted")} disabled={busy}>
                {busy ? "Actualizando..." : "Aceptar consulta"}
              </button>
              <button className="reject-button" onClick={() => onStatusChange("rejected")} disabled={busy}>
                {busy ? "Actualizando..." : "Rechazar"}
              </button>
            </div>
          )}

          <InquiryReplyComposer
            inquiry={inquiry}
            value={replyValue}
            sending={replying}
            notice={replyNotice}
            onChange={onReplyChange}
            onSend={onReply}
          />
        </div>
      )}
    </article>
  )
}

function InquiryReplyComposer({ inquiry, value, sending, notice, onChange, onSend }) {
  const canMessage = ["pending", "accepted"].includes(inquiry.status)
  if (!canMessage) {
    return <p className="inquiry-closed-message">Esta conversación está cerrada.</p>
  }

  return (
    <form className="inquiry-reply-form" onSubmit={(event) => { event.preventDefault(); onSend() }}>
      <label htmlFor={`inquiry-reply-${inquiry.id}`}>Responder en esta conversación</label>
      <textarea
        id={`inquiry-reply-${inquiry.id}`}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder="Escriba su mensaje..."
        rows="3"
        maxLength="1000"
        disabled={sending}
      />
      <div className="inquiry-reply-footer">
        <span>{value.length}/1000</span>
        <button className="reply-button" type="submit" disabled={sending || !value.trim()}>
          {sending ? "Enviando..." : "Enviar respuesta"}
        </button>
      </div>
      {notice && <p className="inquiry-reply-notice" role="status">{notice}</p>}
    </form>
  )
}

function Inquiries() {
  const { token, logout } = useAuth()
  const accountId = getDraftOwnerId(token)
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
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState("")
  const [loadError, setLoadError] = useState("")
  const [syncWarning, setSyncWarning] = useState("")
  const [lastUpdatedAt, setLastUpdatedAt] = useState(null)

  const [updatingInquiry, setUpdatingInquiry] = useState(null)
  const [cancellingInquiry, setCancellingInquiry] = useState(null)

  const [replyMessages, setReplyMessages] = useState(
    () => readInquiryDrafts(getDraftOwnerId(localStorage.getItem("access_token"))),
  )
  const [replyKeys, setReplyKeys] = useState({})
  const [replyNotices, setReplyNotices] = useState({})
  const [replyingInquiry, setReplyingInquiry] = useState(null)
  const [expandedInquiryId, setExpandedInquiryId] = useState(null)
  const loadControllerRef = useRef(null)
  const autoRefreshPausedRef = useRef(false)

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
      setLoadError("Inicie sesión para ver sus consultas.")
      setLoading(false)
      return
    }

    loadControllerRef.current?.abort()
    const controller = new AbortController()
    loadControllerRef.current = controller
    if (background) setRefreshing(true)
    else setLoading(true)
    if (background) setSyncWarning("")
    else setLoadError("")

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
            "No pudimos cargar las consultas enviadas"
        )
      }

      if (!receivedResponse.ok) {
        throw new Error(
          receivedData.detail ||
            "No pudimos cargar las consultas recibidas"
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
      setLastUpdatedAt(new Date())

    } catch (error) {
      if (error.name === "AbortError") return

      console.error("Inquiries error:", error)
      if (background) {
        setSyncWarning("No pudimos actualizar los mensajes nuevos. Las conversaciones ya cargadas siguen disponibles.")
      } else {
        setLoadError(error.message)
      }

    } finally {
      if (loadControllerRef.current === controller) {
        loadControllerRef.current = null
        setLoading(false)
        setRefreshing(false)
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

  async function openInquiry(inquiry) {
    if (expandedInquiryId === inquiry.id) {
      setExpandedInquiryId(null)
      return
    }

    setExpandedInquiryId(inquiry.id)
    const receipts = buildInquiryReadReceipts([inquiry])
    if (receipts.length === 0) return

    const accessToken = localStorage.getItem("access_token")
    if (!accessToken) return

    try {
      const response = await apiFetch("/inquiries/read", {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${accessToken}`,
        },
        body: JSON.stringify({ receipts }),
      })
      if (response.status === 401) {
        logout()
        return
      }
      if (!response.ok) throw new Error("No pudimos marcar la conversación como leída.")
      const markRead = (items) => items.map((item) => item.id === inquiry.id ? { ...item, unread_count: 0 } : item)
      setSentInquiries(markRead)
      setReceivedInquiries(markRead)
      notifyInquiriesChanged()
    } catch {
      setSyncWarning("La conversación está abierta, pero no pudimos sincronizar su estado de lectura.")
    }
  }

  const hasReplyDraft = Object.values(replyMessages).some((message) => message.trim())
  const autoRefreshPaused = hasReplyDraft || Boolean(
    replyingInquiry || updatingInquiry || cancellingInquiry,
  )

  useEffect(() => {
    autoRefreshPausedRef.current = autoRefreshPaused
  }, [autoRefreshPaused])

  useEffect(() => {
    saveInquiryDrafts(accountId, replyMessages)
  }, [accountId, replyMessages])

  useEffect(() => {
    const refreshWhenVisible = () => {
      if (
        !autoRefreshPausedRef.current
        && document.visibilityState === "visible"
        && navigator.onLine !== false
      ) {
        fetchInquiries({ background: true })
      }
    }
    const intervalId = window.setInterval(refreshWhenVisible, 30000)
    document.addEventListener("visibilitychange", refreshWhenVisible)
    window.addEventListener("focus", refreshWhenVisible)
    window.addEventListener("online", refreshWhenVisible)
    return () => {
      window.clearInterval(intervalId)
      document.removeEventListener("visibilitychange", refreshWhenVisible)
      window.removeEventListener("focus", refreshWhenVisible)
      window.removeEventListener("online", refreshWhenVisible)
    }
  }, [fetchInquiries])

  async function updateInquiryStatus(
    inquiryId,
    status
  ) {
    if (
      status === "rejected"
      && !window.confirm("¿Rechazar y cerrar esta consulta? La conversación no podrá volver a abrirse.")
    ) {
      return
    }

    const token =
      localStorage.getItem("access_token")

    if (!token) {
      setError("Inicie sesión.")
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
          getApiError(data, "No pudimos actualizar el estado de la consulta")
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
      setError("Inicie sesión.")
      return
    }

    const replyMessage =
      replyMessages[inquiryId]?.trim()

    if (!replyMessage) {
      setError("Escriba una respuesta.")
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
          getApiError(data, "No pudimos enviar la respuesta")
        )
      }

      setReplyMessages(
        (currentMessages) => ({
          ...currentMessages,
          [inquiryId]: "",
        })
      )
      setReplyKeys((current) => ({ ...current, [inquiryId]: crypto.randomUUID() }))
      setReplyNotices((current) => ({ ...current, [inquiryId]: "Respuesta enviada." }))
      await fetchInquiries({ background: true })

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
    if (!window.confirm("¿Cancelar esta consulta? Esta acción no se puede deshacer.")) {
      return
    }

    const token = localStorage.getItem("access_token")

    if (!token) {
      setError("Inicie sesión.")
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
      const data = await readApiResponse(response)

      if (response.status === 401) {
        logout()
        return
      }

      if (!response.ok) {
        throw new Error(
          getApiError(data, "No pudimos cancelar la consulta")
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
        <p className="inquiry-loading" role="status">Cargando consultas...</p>
      </div>
    )
  }

  return (
    <div className="inquiries-page">

      <div className="inquiries-header">

        <div>
          <h1>Mis consultas</h1>
          <p>Administre sus conversaciones sobre propiedades.</p>
          {lastUpdatedAt && <span>Actualizado el {formatInquiryDate(lastUpdatedAt)}</span>}
          {autoRefreshPaused && <span className="inquiry-refresh-paused">La actualización automática está pausada mientras termina esta acción.</span>}
        </div>

        <button
          type="button"
          onClick={() => fetchInquiries({ background: true })}
          disabled={refreshing}
        >
          {refreshing ? "Actualizando..." : "Actualizar mensajes"}
        </button>

      </div>

      {loadError && (
        <div className="inquiry-load-error" role="alert">
          <p>{loadError}</p>
          <button type="button" onClick={fetchInquiries}>Intentar de nuevo</button>
        </div>
      )}

      {error && (
        <p className="inquiry-error" role="alert">{error}</p>
      )}

      {syncWarning && (
        <div className="inquiry-sync-warning" role="status">
          <span>{syncWarning}</span>
          <button type="button" onClick={() => fetchInquiries({ background: true })}>Intentar de nuevo</button>
        </div>
      )}

      {propertyReference && (
        <div className="inquiry-property-filter" role="status">
          <span>Mostrando conversaciones de <strong>{propertyReference}</strong>.</span>
          <button type="button" onClick={clearPropertyFilter}>Mostrar todas las consultas</button>
        </div>
      )}

      {/* SENT INQUIRIES */}

      {!loadError && <section className="inquiries-section">

        <h2>Consultas enviadas</h2>

        {sentMeta.counts.all === 0 ? (

          <p>
            Todavía no ha enviado ninguna consulta.
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
              No hay consultas enviadas con este estado.
            </p>
          ) : (

          <div className="inquiries-grid">

            {sentInquiries.map((inquiry) => (
              <InquiryCard
                key={inquiry.id}
                inquiry={inquiry}
                viewerRole="buyer"
                direction="sent"
                expanded={expandedInquiryId === inquiry.id}
                cancelling={cancellingInquiry === inquiry.id}
                replyValue={replyMessages[inquiry.id] || ""}
                replyNotice={replyNotices[inquiry.id] || ""}
                replying={replyingInquiry === inquiry.id}
                onToggle={() => openInquiry(inquiry)}
                onCancel={() => cancelInquiry(inquiry.id)}
                onReplyChange={(message) => {
                  setReplyMessages((current) => ({ ...current, [inquiry.id]: message }))
                  setReplyNotices((current) => ({ ...current, [inquiry.id]: "" }))
                }}
                onReply={() => sendInquiryMessage(inquiry.id)}
              />
            ))}

          </div>

          )}

          <InquiryPagination page={sentPage} totalPages={sentMeta.totalPages} onChange={setSentPage} />

          </>

        )}

      </section>}

      {/* RECEIVED INQUIRIES */}

      {!loadError && <section className="inquiries-section">

        <h2>Consultas recibidas</h2>

        {receivedMeta.counts.all === 0 ? (

          <p>
            Todavía no ha recibido ninguna consulta.
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
              No hay consultas recibidas con este estado.
            </p>
          ) : (

          <div className="inquiries-grid">

            {receivedInquiries.map((inquiry) => (
              <InquiryCard
                key={inquiry.id}
                inquiry={inquiry}
                viewerRole="seller"
                direction="received"
                expanded={expandedInquiryId === inquiry.id}
                busy={updatingInquiry === inquiry.id}
                replyValue={replyMessages[inquiry.id] || ""}
                replyNotice={replyNotices[inquiry.id] || ""}
                replying={replyingInquiry === inquiry.id}
                onToggle={() => openInquiry(inquiry)}
                onStatusChange={(status) => updateInquiryStatus(inquiry.id, status)}
                onReplyChange={(message) => {
                  setReplyMessages((current) => ({ ...current, [inquiry.id]: message }))
                  setReplyNotices((current) => ({ ...current, [inquiry.id]: "" }))
                }}
                onReply={() => sendInquiryMessage(inquiry.id)}
              />
            ))}

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
