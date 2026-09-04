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
    : { loading: false, error: "This verification link is incomplete." })

  useEffect(() => {
    if (!token) return
    let active = true
    apiFetch("/users/email-verification/confirm", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }),
    }).then(async (response) => {
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "Could not verify your email"))
      if (active) setStatus({ loading: false, error: "" })
    }).catch((error) => {
      if (active) setStatus({ loading: false, error: error.message })
    })
    return () => { active = false }
  }, [token])

  return (
    <AuthLayout eyebrow="Account security">
      <p className="auth-card-eyebrow">Identity check</p>
      <h1>Email verification</h1>
      {status.loading && <p className="auth-intro" role="status">Verifying your email…</p>}
      {!status.loading && !status.error && <p className="auth-success" role="status">Your email is verified. Your account is ready.</p>}
      {status.error && <p className="auth-error" role="alert">{status.error}</p>}
      <p className="auth-switch"><Link to="/account">Go to my account</Link></p>
    </AuthLayout>
  )
}

export default VerifyEmail
