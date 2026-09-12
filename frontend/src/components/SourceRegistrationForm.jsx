import { useRef, useState } from "react"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"

export default function SourceRegistrationForm({ token, onCreated, onCancel }) {
  const submitting = useRef(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting.current) return
    const values = new FormData(event.currentTarget)
    const payload = Object.fromEntries(Array.from(values, ([key, value]) => [key, value.trim()]))
    payload.country_code = "DO"
    payload.stale_after_hours = Number(payload.stale_after_hours)
    submitting.current = true
    setSaving(true)
    setError("")
    try {
      const response = await apiFetch("/catalog/admin/sources", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}`, "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      })
      const data = await readApiResponse(response)
      if (response.status === 422) throw new Error("Revise los datos: complete los campos y use un enlace HTTPS válido para la licencia.")
      if (!response.ok) throw new Error(getApiError(data, "No pudimos registrar el proveedor. Intente de nuevo."))
      if (!Number.isInteger(data?.id) || data.id <= 0) {
        throw new Error("No pudimos confirmar el registro. Actualice la lista antes de intentarlo nuevamente.")
      }
      onCreated(data)
    } catch (saveError) {
      setError(saveError.message)
    } finally {
      submitting.current = false
      setSaving(false)
    }
  }

  return (
    <form className="source-registration" onSubmit={handleSubmit} aria-labelledby="source-registration-title" aria-busy={saving}>
      <h2 id="source-registration-title">Registrar proveedor</h2>
      <p>Agregue una agencia o desarrollador con inventario en República Dominicana. Quedará pendiente de revisión; este registro no aprueba permisos ni publica propiedades.</p>
      <fieldset disabled={saving}>
        <legend className="sr-only">Datos del proveedor</legend>
        <div className="source-form-grid">
          <label htmlFor="source-name">Nombre del proveedor
            <input id="source-name" name="name" required minLength={2} maxLength={150} autoComplete="organization" />
          </label>
          <label htmlFor="source-key">Identificador del proveedor
            <input id="source-key" name="source_key" required minLength={2} maxLength={64} pattern={"[a-z0-9][a-z0-9_\\-]{1,63}"} autoCapitalize="none" spellCheck={false} aria-describedby="source-key-help" />
            <span id="source-key-help">Un código único con letras minúsculas, números o guiones. Ejemplo: agencia-cibao.</span>
          </label>
          <label htmlFor="source-license-name">Nombre de la licencia o acuerdo
            <input id="source-license-name" name="license_name" required minLength={2} maxLength={150} />
          </label>
          <label htmlFor="source-license-url">Enlace a las condiciones de uso
            <input id="source-license-url" name="license_url" type="url" required maxLength={1000} pattern="https://.*" placeholder="https://" aria-describedby="source-license-help" />
            <span id="source-license-help">Use el enlace HTTPS oficial. La autorización de republicación se revisa por separado.</span>
          </label>
          <label htmlFor="source-attribution">Crédito del proveedor
            <input id="source-attribution" name="attribution" required minLength={2} maxLength={300} aria-describedby="source-attribution-help" />
            <span id="source-attribution-help">Texto que acompañará sus anuncios, por ejemplo: Cortesía de Agencia Cibao.</span>
          </label>
          <label htmlFor="source-freshness">Vigencia del inventario (horas)
            <input id="source-freshness" name="stale_after_hours" type="number" required min={1} max={720} step={1} defaultValue={48} aria-describedby="source-freshness-help" />
            <span id="source-freshness-help">Plazo máximo sin actualizar los datos, según lo acordado con el proveedor.</span>
          </label>
        </div>
        {error && <p className="sources-error" role="alert">{error}</p>}
        <div className="source-form-actions">
          <button type="submit">{saving ? "Guardando…" : "Guardar como pendiente"}</button>
          <button type="button" className="source-cancel" onClick={onCancel}>Cancelar</button>
        </div>
      </fieldset>
    </form>
  )
}
