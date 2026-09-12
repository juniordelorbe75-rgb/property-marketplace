import { useEffect, useState } from "react"
import { Link, useSearchParams } from "react-router-dom"
import { createEmailVerifier } from "../utils/emailVerification"
import AuthLayout from "../components/AuthLayout"
import "./auth.css"

function VerifyEmail() {
  const [searchParams] = useSearchParams()
  const token = searchParams.get("token") || ""
  const [verify] = useState(() => createEmailVerifier())
  const [result, setResult] = useState(null)
  const status = result?.token === token ? result : {
    loading: Boolean(token),
    error: token ? "" : "Este enlace de verificación está incompleto.",
  }

  useEffect(() => {
    if (!token) return
    let active = true
    verify(token).then(() => {
      if (active) setResult({ token, loading: false, error: "" })
    }).catch((error) => {
      if (active) setResult({ token, loading: false, error: error.message })
    })
    return () => { active = false }
  }, [token, verify])

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
