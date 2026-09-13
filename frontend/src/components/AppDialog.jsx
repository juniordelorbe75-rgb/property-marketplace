import { useEffect, useRef } from "react"
import { createPortal } from "react-dom"
import "./AppDialog.css"

function AppDialog({ dialog, onClose }) {
  const confirmRef = useRef(null)

  useEffect(() => {
    if (!dialog) return undefined
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = "hidden"
    confirmRef.current?.focus()

    const handleKeyDown = (event) => {
      if (event.key === "Escape") onClose(false)
    }
    window.addEventListener("keydown", handleKeyDown)

    return () => {
      document.body.style.overflow = previousOverflow
      window.removeEventListener("keydown", handleKeyDown)
    }
  }, [dialog, onClose])

  if (!dialog) return null

  return createPortal(
    <div
      className="app-dialog-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose(false)
      }}
    >
      <section
        className={`app-dialog app-dialog-${dialog.tone || "default"}`}
        role="dialog"
        aria-modal="true"
        aria-labelledby="app-dialog-title"
        aria-describedby="app-dialog-message"
      >
        <span className="app-dialog-mark" aria-hidden="true">
          {dialog.tone === "danger" ? "!" : "✓"}
        </span>
        <p className="app-dialog-eyebrow">HabitaRD</p>
        <h2 id="app-dialog-title">{dialog.title}</h2>
        <p id="app-dialog-message">{dialog.message}</p>
        <div className="app-dialog-actions">
          {dialog.mode === "confirm" && (
            <button type="button" className="app-dialog-cancel" onClick={() => onClose(false)}>
              {dialog.cancelLabel || "Volver"}
            </button>
          )}
          <button
            ref={confirmRef}
            type="button"
            className="app-dialog-confirm"
            onClick={() => onClose(true)}
          >
            {dialog.confirmLabel || (dialog.mode === "confirm" ? "Confirmar" : "Entendido")}
          </button>
        </div>
      </section>
    </div>,
    document.body,
  )
}

export default AppDialog
