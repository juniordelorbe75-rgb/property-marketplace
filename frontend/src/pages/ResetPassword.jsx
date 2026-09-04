import { useMemo, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import PasswordInput from "../components/PasswordInput"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { queueLoginWelcome } from "../utils/loginWelcomeSession"
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
    if (password !== confirmation) {
      setError("Passwords do not match")
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
      if (!response.ok) throw new Error(getApiError(data, "Could not reset your password"))
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
      <main className="auth-page"><section className="auth-card">
        <h1>Reset link missing</h1>
        <p className="auth-error" role="alert">This password reset link is incomplete.</p>
        <p className="auth-switch"><Link to="/forgot-password">Request a new link</Link></p>
      </section></main>
    )
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <h1>Create a new password</h1>
        <p className="auth-intro">Use at least 8 characters and choose a password you don’t use elsewhere.</p>
        <form className="auth-form" onSubmit={handleSubmit}>
          <PasswordInput id="reset-password" label="New password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete="new-password" minLength={8} />
          <PasswordInput id="reset-password-confirmation" label="Confirm new password" value={confirmation} onChange={(event) => setConfirmation(event.target.value)} autoComplete="new-password" minLength={8} invalid={Boolean(confirmation) && password !== confirmation} />
          {error && <p className="auth-error" role="alert">{error}</p>}
          <button className="auth-submit" type="submit" disabled={loading || password.length < 8 || password !== confirmation}>{loading ? "Resetting..." : "Reset password"}</button>
        </form>
        <p className="auth-switch"><Link to="/login">Back to login</Link></p>
      </section>
    </main>
  )
}

export default ResetPassword
