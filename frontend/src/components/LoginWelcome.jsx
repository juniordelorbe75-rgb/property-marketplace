import { useEffect, useState } from "react"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../utils/apiFetch"
import { readApiResponse } from "../utils/apiResponse"
import {
  LOGIN_WELCOME_DURATION_MS,
  LOGIN_WELCOME_KEY,
} from "../utils/loginWelcomeSession"
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
        const firstName = user.first_name || user.name?.trim().split(/\s+/)[0] || ""
        sessionStorage.removeItem(LOGIN_WELCOME_KEY)
        setWelcome({ firstName, kind })
      })
      .catch((error) => {
        if (error.name !== "AbortError") sessionStorage.removeItem(LOGIN_WELCOME_KEY)
      })

    return () => controller.abort()
  }, [token])

  useEffect(() => {
    if (!welcome) return undefined
    const timer = window.setTimeout(() => setWelcome(null), LOGIN_WELCOME_DURATION_MS)
    return () => window.clearTimeout(timer)
  }, [welcome])

  if (!token || !welcome) return null

  return (
    <aside className="login-welcome" aria-live="polite">
      <div>
        <strong>{welcome.kind === "new"
          ? `¡Bienvenido${welcome.firstName ? `, ${welcome.firstName}` : ""} a HabitaRD!`
          : `¡Bienvenido nuevamente${welcome.firstName ? `, ${welcome.firstName}` : ""}!`}</strong>
        <span>{welcome.kind === "new" ? "Ya puede explorar oportunidades para comprar, alquilar o vender." : "Nos alegra tenerle de vuelta. Continúe donde lo dejó."}</span>
      </div>
      <button
        type="button"
        onClick={() => setWelcome(null)}
        aria-label="Cerrar mensaje de bienvenida"
        title="Cerrar"
      >×</button>
    </aside>
  )
}

export default LoginWelcome
