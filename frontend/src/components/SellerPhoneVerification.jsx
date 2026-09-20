import { useState } from "react"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { getSellerRegistrationFields } from "../utils/sellerDetails"

export default function SellerPhoneVerification({ details, verifiedPhone, onVerified, idPrefix = "register", purpose = "crear su cuenta" }) {
  const [challengeToken, setChallengeToken] = useState("")
  const [challengePhone, setChallengePhone] = useState("")
  const [code, setCode] = useState("")
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState("")
  const [message, setMessage] = useState("")

  async function requestCode() {
    if (busy) return
    setError("")
    setMessage("")
    setChallengeToken("")
    setChallengePhone("")
    onVerified("", "")

    try {
      const { seller_phone: phone } = getSellerRegistrationFields("seller", details)
      setBusy(true)
      const response = await apiFetch("/users/seller-phone-verification/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) {
        throw new Error(getApiError(data, "No pudimos enviar el código SMS."))
      }
      setChallengeToken(data.challenge_token)
      setChallengePhone(phone)
      setCode("")
      setMessage("Le enviamos un código por SMS. Escríbalo aquí para validar su teléfono.")
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  async function confirmCode() {
    if (busy || !challengeToken || !code) return
    setError("")
    setMessage("")
    setBusy(true)

    try {
      const { seller_phone: phone } = getSellerRegistrationFields("seller", details)
      if (phone !== challengePhone) {
        throw new Error("El teléfono cambió. Solicite un código nuevo.")
      }
      const response = await apiFetch("/users/seller-phone-verification/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge_token: challengeToken, code: code.trim() }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) {
        throw new Error(getApiError(data, "No pudimos validar el código SMS."))
      }
      onVerified(phone, data.phone_verification_token)
      setChallengeToken("")
      setChallengePhone("")
      setCode("")
      setMessage(`Teléfono validado. Ya puede ${purpose}.`)
    } catch (confirmError) {
      setError(confirmError.message)
    } finally {
      setBusy(false)
    }
  }

  const isVerified = Boolean(verifiedPhone) && verifiedPhone ===
    (details.seller_phone || "").replace(/[\s().-]/g, "")

  return (
    <div className="auth-phone-verification">
      <p>Valide el teléfono de contacto antes de {purpose}.</p>
      <button type="button" className="auth-link-button" onClick={requestCode} disabled={busy}>
        {isVerified ? "Enviar un código nuevo" : "Enviar código por SMS"}
      </button>
      {challengeToken && (
        <div className="auth-field">
          <label htmlFor={`${idPrefix}-sms-code`}>Código SMS</label>
          <input
            id={`${idPrefix}-sms-code`}
            type="text"
            inputMode="numeric"
            autoComplete="one-time-code"
            pattern="[0-9]{4,10}"
            value={code}
            onChange={(event) => setCode(event.target.value)}
            maxLength={10}
          />
          <button type="button" className="auth-link-button" onClick={confirmCode} disabled={busy || !/^[0-9]{4,10}$/.test(code)}>
            Validar teléfono
          </button>
        </div>
      )}
      {error && <p className="auth-error" role="alert">{error}</p>}
      {message && <p className="auth-success" role="status">{message}</p>}
    </div>
  )
}
