import { useMemo, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import PasswordInput from "../components/PasswordInput"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { queueLoginWelcome } from "../utils/loginWelcomeSession"
import AuthLayout from "../components/AuthLayout"
import "./auth.css"

function ResetPassword() {
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()
  const { login } = useAuth()
  const token = useMemo(() => searchParams.get("token") || "", [searchParams])
  const [password, setPassword] = useState("")
  const [confirmation, setConfirmation] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    if (loading) return
    if (password !== confirmation) {
      setError("Las contraseñas no coinciden")
      return
    }
    setError("")
    setLoading(true)
    try {
      const response = await apiFetch("/users/password-reset/confirm", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, new_password: password }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "No pudimos restablecer su contraseña"))
      login(data.access_token)
      queueLoginWelcome("returning")
      navigate("/account", { replace: true, state: { passwordReset: true } })
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  if (!token) {
    return (
      <AuthLayout eyebrow="Recuperación de cuenta">
        <h1>Falta el enlace de recuperación</h1>
        <p className="auth-error" role="alert">Este enlace de recuperación está incompleto.</p>
        <p className="auth-switch"><Link to="/forgot-password">Solicitar un enlace nuevo</Link></p>
      </AuthLayout>
    )
  }

  return (
    <AuthLayout eyebrow="Recuperación de cuenta">
        <p className="auth-card-eyebrow">Recuperación segura</p>
        <h1>Crear una contraseña nueva</h1>
        <p className="auth-intro">Use al menos 8 caracteres y una contraseña que no utilice en otros servicios.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <PasswordInput id="reset-password" label="Contraseña nueva" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" minLength={8} />
          <PasswordInput id="reset-password-confirmation" label="Confirmar contraseña nueva" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="new-password" minLength={8} invalid={Boolean(confirmation) && password !== confirmation} />
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-submit" type="submit" disabled={loading || password.length < 8 || password !== confirmation}>{loading ? "Restableciendo..." : "Restablecer contraseña"}</button>
        </form>
        <p className="auth-switch"><Link to="/login">Volver a iniciar sesión</Link></p>
    </AuthLayout>
  )
}

export default ResetPassword
