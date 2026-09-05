import { useEffect, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { apiFetch } from "../utils/apiFetch"
import { getSafeReturnPath } from "../utils/authRedirect"
import { queueLoginWelcome } from "../utils/loginWelcomeSession"
import PasswordInput from "../components/PasswordInput"
import AuthLayout from "../components/AuthLayout"
import "./auth.css"

function Login() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const returnTo = getSafeReturnPath(location.state?.returnTo)

  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)
  const [providers, setProviders] = useState([])
  const [providersLoaded, setProvidersLoaded] = useState(false)

  useEffect(() => {
    apiFetch("/auth/providers")
      .then((response) => response.ok ? response.json() : { providers: [] })
      .then((data) => setProviders(data.providers || []))
      .catch(() => setProviders([]))
      .finally(() => setProvidersLoaded(true))
  }, [])

  function socialLogin(provider) {
    const query = new URLSearchParams({ return_to: returnTo })
    window.location.assign(`/auth/${provider}/start?${query}`)
  }

  async function handleLogin(event) {
    event.preventDefault()

    if (loading) return

    setError("")
    setLoading(true)

    try {
      const response = await apiFetch("/users/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "No pudimos iniciar la sesión"))

      login(data.access_token)
      queueLoginWelcome("returning")
      navigate(returnTo, { replace: true })
    } catch (loginError) {
      console.error("Login error:", loginError)
      setError(loginError.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <AuthLayout>
      <p className="auth-card-eyebrow">Bienvenido nuevamente</p>
      <h1>Inicie sesión en su cuenta</h1>

      <p className="auth-intro">Continúe administrando sus propiedades guardadas y conversaciones.</p>

      {location.state?.sessionExpired && (
        <p className="auth-session-note" role="status">
          Su sesión venció o fue revocada. Inicie sesión nuevamente para continuar de forma segura.
        </p>
      )}

      {returnTo !== "/" && <p className="auth-return-note">Después de iniciar sesión, regresará al punto donde estaba.</p>}

      <form className="auth-form" onSubmit={handleLogin}>
        <div className="auth-field">
          <label htmlFor="login-email">Correo electrónico</label>

          <input
            id="login-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </div>

        <PasswordInput
          id="login-password"
          label="Contraseña"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="current-password"
        />

        <div className="auth-forgot-link"><Link to="/forgot-password">¿Olvidó su contraseña?</Link></div>

        {error && <p className="auth-error" role="alert">{error}</p>}

        <button className="auth-submit" type="submit" disabled={loading}>
          {loading ? "Iniciando sesión..." : "Iniciar sesión"}
        </button>
      </form>

      {providersLoaded && providers.length > 0 && (
        <section className="social-login" aria-label="Opciones de inicio de sesión social">
          <p><span>o continuar con</span></p>
          {providers.map((provider) => (
            <button
              key={provider.id}
              type="button"
              disabled={!provider.enabled}
              title={provider.enabled ? `Continuar con ${provider.name}` : `El acceso con ${provider.name} todavía no está configurado`}
              onClick={() => socialLogin(provider.id)}
            >
              Continuar con {provider.name}{provider.enabled ? "" : " — próximamente"}
            </button>
          ))}
          {!providers.some((provider) => provider.enabled) && (
            <small className="social-login-note">El acceso social se activará cuando el administrador termine de configurar los proveedores.</small>
          )}
        </section>
      )}

      <p className="auth-switch">
        ¿Necesita una cuenta?{" "}
        <Link to="/register" state={{ returnTo }}>Registrarse</Link>
      </p>
    </AuthLayout>
  )
}

export default Login
