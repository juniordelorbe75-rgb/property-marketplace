import { useState } from "react"
import { Link } from "react-router-dom"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import AuthLayout from "../components/AuthLayout"
import "./auth.css"

function ForgotPassword() {
  const [email, setEmail] = useState("")
  const [error, setError] = useState("")
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (loading) return
    setError("")
    setLoading(true)
    try {
      const response = await apiFetch("/users/password-reset/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "No pudimos solicitar el enlace de recuperación"))
      setSent(true)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout eyebrow="Recuperación de cuenta">
        <p className="auth-card-eyebrow">Recuperación segura</p>
        <h1>¿Olvidó su contraseña?</h1>
        {sent ? (
          <>
            <p className="auth-success" role="status">Si existe una cuenta con ese correo, enviamos un enlace de recuperación. Vence en 30 minutos.</p>
            <p className="auth-intro">Revise su bandeja de entrada y la carpeta de correo no deseado.</p>
          </>
        ) : (
          <>
            <p className="auth-intro">Ingrese el correo de su cuenta y le enviaremos un enlace seguro.</p>
            <form className="auth-form" onSubmit={handleSubmit}>
              <div className="auth-field">
                <label htmlFor="reset-email">Correo electrónico</label>
                <input id="reset-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoFocus />
              </div>
              {error && <p className="auth-error" role="alert">{error}</p>}
              <button className="auth-submit" type="submit" disabled={loading}>{loading ? "Enviando..." : "Enviar enlace"}</button>
            </form>
          </>
        )}
        <p className="auth-switch"><Link to="/login">Volver a iniciar sesión</Link></p>
    </AuthLayout>
  )
}

export default ForgotPassword
