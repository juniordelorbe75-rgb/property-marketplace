import { useEffect, useState } from "react"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../utils/apiFetch"
import { readApiResponse } from "../utils/apiResponse"
import { LOGIN_WELCOME_KEY } from "../utils/loginWelcomeSession"
import "./LoginWelcome.css"

function LoginWelcome() {
  const { token } = useAuth()
  const [welcome, setWelcome] = useState(null)

  useEffect(() => {
    const kind = sessionStorage.getItem(LOGIN_WELCOME_KEY)
    if (!token) {
      sessionStorage.removeItem(LOGIN_WELCOME_KEY)
      return
    }
    if (!kind) return

    const controller = new AbortController()
    apiFetch("/users/me", {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then(async (response) => {
        const data = await readApiResponse(response)
        if (!response.ok) throw new Error("Unable to load welcome profile")
        return data
      })
      .then((user) => {
        const firstName = user.first_name || user.name?.trim().split(/\s+/)[0] || "there"
        sessionStorage.removeItem(LOGIN_WELCOME_KEY)
        setWelcome({ firstName, kind })
      })
      .catch((error) => {
        if (error.name !== "AbortError") sessionStorage.removeItem(LOGIN_WELCOME_KEY)
      })

    return () => controller.abort()
  }, [token])

  if (!token || !welcome) return null

  return (
    <aside className="login-welcome" aria-live="polite">
      <div>
        <strong>{welcome.kind === "new" ? `Welcome to Property Marketplace, ${welcome.firstName}!` : `Welcome back, ${welcome.firstName}!`}</strong>
        <span>{welcome.kind === "new" ? "Your next opportunity is ready to explore." : "It’s good to see you again. Let’s find what moves you forward."}</span>
      </div>
      <button type="button" onClick={() => setWelcome(null)} aria-label="Dismiss welcome message">×</button>
    </aside>
  )
}

export default LoginWelcome
