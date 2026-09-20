import { useState } from "react"

import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { compactSellerPhone, normalizeSellerPhone } from "../utils/sellerDetails"

export default function SellerPhoneVerificationPanel({ phone, currentPhone, proof, onProofChange, disabled = false }) {
  const [challengeToken, setChallengeToken] = useState("")
  const [challengePhone, setChallengePhone] = useState("")
  const [code, setCode] = useState("")
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  const normalizedPhone = compactSellerPhone(phone)
  const changed = normalizedPhone !== compactSellerPhone(currentPhone)
  const verified = changed && proof?.phone === normalizedPhone && Boolean(proof?.token)
  const pending = Boolean(challengeToken) && challengePhone === normalizedPhone

  async function requestCode() {
    if (busy || disabled) return
    setError("")
    setMessage("")
    setChallengeToken("")
    setChallengePhone("")
    onProofChange(null)

    try {
      const number = normalizeSellerPhone(phone)
      setBusy(true)
      const response = await apiFetch("/users/seller-phone-verification/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone: number }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "No pudimos enviar el código SMS."))
      if (!data.challenge_token) throw new Error("El servidor no devolvió una solicitud válida.")
      setChallengeToken(data.challenge_token)
      setChallengePhone(number)
      setCode("")
      setMessage("Código enviado por SMS. Ingréselo para verificar el nuevo teléfono.")
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setBusy(false)
    }
  }

  async function confirmCode() {
    if (busy || disabled || !pending) return
    setError("")
    setMessage("")

    try {
      const number = normalizeSellerPhone(phone)
      if (number !== challengePhone) throw new Error("El teléfono cambió. Solicite un código nuevo.")
      setBusy(true)
      const response = await apiFetch("/users/seller-phone-verification/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ challenge_token: challengeToken, code: code.trim() }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "No pudimos verificar el código SMS."))
      if (!data.phone_verification_token) throw new Error("El servidor no confirmó el teléfono.")
      onProofChange({ phone: number, token: data.phone_verification_token })
      setChallengeToken("")
      setChallengePhone("")
      setCode("")
      setMessage("Nuevo teléfono verificado. Ya puede guardar los cambios.")
    } catch (confirmError) {
      setError(confirmError.message)
    } finally {
      setBusy(false)
    }
  }

  if (!changed) {
    return <div className="seller-phone-verification is-current"><strong>Teléfono actual</strong><p>El número no ha cambiado.</p></div>
  }

  return (
    <div className={`seller-phone-verification${verified ? " is-verified" : ""}`}>
      <strong>Verificación del nuevo teléfono</strong>
      <p>Antes de guardar este número, solicite y confirme un código por SMS.</p>
      <button type="button" className="secondary-button" onClick={requestCode} disabled={busy || disabled}>
        {verified ? "Enviar un código nuevo" : "Enviar código por SMS"}
      </button>
      {pending && !verified && (
        <div className="seller-phone-code">
          <label htmlFor="account-seller-phone-code">Código SMS</label>
          <input id="account-seller-phone-code" type="text" inputMode="numeric" autoComplete="one-time-code" pattern="[0-9]{4,10}" maxLength={10} value={code} onChange={(event) => setCode(event.target.value)} disabled={busy || disabled} />
          <button type="button" className="secondary-button" onClick={confirmCode} disabled={busy || disabled || !/^[0-9]{4,10}$/.test(code.trim())}>Verificar código</button>
        </div>
      )}
      {message && <p className={verified ? "seller-phone-verification-success" : "seller-phone-verification-message"} role="status">{message}</p>}
      {error && <p className="seller-phone-verification-error" role="alert">{error}</p>}
    </div>
  )
}
