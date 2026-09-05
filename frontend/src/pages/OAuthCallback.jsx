import { useEffect, useRef, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { getSafeReturnPath } from "../utils/authRedirect"
import { queueLoginWelcome } from "../utils/loginWelcomeSession"

function OAuthCallback() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { login } = useAuth()
  const started = useRef(false)
  const [error, setError] = useState(params.get("error") || "")

  useEffect(() => {
    const code = params.get("code")
    if (!code || error || started.current) return
    started.current = true

    apiFetch("/auth/exchange", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    })
      .then(async (response) => {
        const data = await readApiResponse(response)
        if (!response.ok) throw new Error(getApiError(data, "No pudimos completar el acceso social"))
        return data
      })
      .then((data) => {
        login(data.access_token)
        queueLoginWelcome("returning")
        navigate(getSafeReturnPath(params.get("return_to")), { replace: true })
      })
      .catch((requestError) => setError(requestError.message))
  }, [error, login, navigate, params])

  return (
    <main className="auth-callback">
      <h1>{error ? "No pudimos completar el inicio de sesión" : "Completando inicio de sesión…"}</h1>
      {error && <><p role="alert">{error}</p><Link to="/login">Volver al inicio de sesión</Link></>}
    </main>
  )
}

export default OAuthCallback
