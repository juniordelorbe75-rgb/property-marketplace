import { useState } from "react"
import { Link } from "react-router-dom"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import "./auth.css"

function ForgotPassword() {
  const [email, setEmail] = useState("")
  const [error, setError] = useState("")
  const [sent, setSent] = useState(false)
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event) {
    event.preventDefault()
    setError("")
    setLoading(true)
    try {
      const response = await apiFetch("/users/password-reset/request", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "Could not request a reset link"))
      setSent(true)
    } catch (requestError) {
      setError(requestError.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card">
        <h1>Forgot password?</h1>
        {sent ? (
          <>
            <p className="auth-success" role="status">If an account exists for that email, we sent a reset link. It expires in 30 minutes.</p>
            <p className="auth-intro">Check your inbox and spam folder. During local development, the link appears in the backend terminal.</p>
          </>
        ) : (
          <>
            <p className="auth-intro">Enter your account email and we’ll send you a secure reset link.</p>
            <form className="auth-form" onSubmit={handleSubmit}>
              <div className="auth-field">
                <label htmlFor="reset-email">Email</label>
                <input id="reset-email" type="email" autoComplete="email" value={email} onChange={(event) => setEmail(event.target.value)} required autoFocus />
              </div>
              {error && <p className="auth-error" role="alert">{error}</p>}
              <button className="auth-submit" type="submit" disabled={loading}>{loading ? "Sending..." : "Send reset link"}</button>
            </form>
          </>
        )}
        <p className="auth-switch"><Link to="/login">Back to login</Link></p>
      </section>
    </main>
  )
}

export default ForgotPassword
