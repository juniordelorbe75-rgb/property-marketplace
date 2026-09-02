import { useEffect, useState } from "react"
import { Link, useLocation, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { apiFetch } from "../utils/apiFetch"
import { getSafeReturnPath } from "../utils/authRedirect"

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

  useEffect(() => {
    apiFetch("/auth/providers")
      .then((response) => response.ok ? response.json() : { providers: [] })
      .then((data) => setProviders(data.providers || []))
      .catch(() => setProviders([]))
  }, [])

  function socialLogin(provider) {
    const query = new URLSearchParams({ return_to: returnTo })
    window.location.assign(`/auth/${provider}/start?${query}`)
  }

  function handleLogin(event) {
    event.preventDefault()

    setError("")
    setLoading(true)

    apiFetch("/users/login", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        email: email,
        password: password,
      }),
    })
      .then(async (response) => {
        const data = await readApiResponse(response)

        if (!response.ok) {
          throw new Error(getApiError(data, "Login failed"))
        }

        return data
      })
      .then((data) => {
        login(data.access_token)

        setLoading(false)

        navigate(returnTo, { replace: true })
      })
      .catch((error) => {
        console.error("Login error:", error)
        setError(error.message)
        setLoading(false)
      })
  }

  return (
    <div>
      <h1>Login</h1>

      <p>Login to your account.</p>

      {providers.length > 0 && (
        <section className="social-login" aria-label="Social sign-in options">
          {providers.map((provider) => (
            <button key={provider.id} type="button" onClick={() => socialLogin(provider.id)}>
              Continue with {provider.name}
            </button>
          ))}
          <p><span>or use your email and password</span></p>
        </section>
      )}

      {returnTo !== "/" && <p>After login, you will return to where you left off.</p>}

      <form onSubmit={handleLogin}>
        <div>
          <label>Email</label>
          <br />

          <input
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
        </div>

        <div>
          <label>Password</label>
          <br />

          <input
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
        </div>

        {error && <p>{error}</p>}

        <button type="submit" disabled={loading}>
          {loading ? "Logging in..." : "Login"}
        </button>
      </form>

      <p>
        Need an account?{" "}
        <Link to="/register" state={{ returnTo }}>Register</Link>
      </p>
    </div>
  )
}

export default Login
