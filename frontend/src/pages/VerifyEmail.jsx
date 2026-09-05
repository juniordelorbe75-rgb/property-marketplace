import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import AuthLayout from "../components/AuthLayout"
import "./auth.css"

function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get("token") || ""
  const [status, setStatus] = useState(() => token
    ? { loading: true, error: "" }
    : { loading: false, error: "Este enlace de verificación está incompleto." })

  useEffect(() => {
    if (!token) return
    let active = true
    apiFetch("/users/email-verification/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    }).then(async (response) => {
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "No pudimos verificar su correo electrónico"))
      if (active) setStatus({ loading: false, error: "" })
    }).catch((error) => {
      if (active) setStatus({ loading: false, error: error.message })
    })
    return () => { active = false }
  }, [token])

  return (
    <AuthLayout eyebrow="Seguridad de la cuenta">
      <p className="auth-card-eyebrow">Verificación de identidad</p>
      <h1>Verificación del correo</h1>
      {status.loading && <p className="auth-intro" role="status">Verificando su correo…</p>}
      {!status.loading && !status.error && <p className="auth-success" role="status">Su correo está verificado. La cuenta está lista.</p>}
      {status.error && <p className="auth-error" role="alert">{status.error}</p>}
      <p className="auth-switch"><Link to="/account">Ir a mi cuenta</Link></p>
    </AuthLayout>
  )
}

export default VerifyEmail
