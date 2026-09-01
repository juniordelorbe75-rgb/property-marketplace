import { useState } from "react"
import { useLocation, useNavigate, Link } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { apiFetch } from "../utils/apiFetch"
import { getSafeReturnPath } from "../utils/authRedirect"

function Register() {
  const navigate = useNavigate()
  const location = useLocation()
  const { login } = useAuth()
  const returnTo = getSafeReturnPath(location.state?.returnTo)

  const [name, setName] = useState("")
  const [email, setEmail] = useState("")
  const [password, setPassword] = useState("")

  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleRegister(event) {
    event.preventDefault()

    setError("")
    setLoading(true)

    try {
      const response = await apiFetch(
        "/users/",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            name,
            email,
            password,
          }),
        }
      )

      const data = await readApiResponse(response)

      if (!response.ok) {
        throw new Error(
          getApiError(data, "Registration failed")
        )
      }

         const loginResponse = await apiFetch(
      "/users/login",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          email,
          password,
        }),
      }
    )

    const loginData = await readApiResponse(loginResponse)

    if (!loginResponse.ok) {
      throw new Error(
        getApiError(
          loginData,
          "Account created, but automatic login failed"
        )
      )
    }

    login(loginData.access_token)

    navigate(returnTo, { replace: true })

    } catch (error) {
      console.error("Registration error:", error)
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <h1>Create Account</h1>

      <p>Register for your property marketplace account.</p>

      <form onSubmit={handleRegister}>

        <div>
          <label>Name</label>
          <br />

          <input
            type="text"
            value={name}
            onChange={(event) =>
              setName(event.target.value)
            }
            required
          />
        </div>

        <div>
          <label>Email</label>
          <br />

          <input
            type="email"
            value={email}
            onChange={(event) =>
              setEmail(event.target.value)
            }
            required
          />
        </div>

        <div>
          <label>Password</label>
          <br />

          <input
            type="password"
            value={password}
            onChange={(event) =>
              setPassword(event.target.value)
            }
            required
          />
        </div>

        {error && <p>{error}</p>}

        <button
          type="submit"
          disabled={loading}
        >
          {loading
            ? "Creating Account..."
            : "Create Account"}
        </button>

      </form>

      <p>
        Already have an account?{" "}
        <Link to="/login" state={{ returnTo }}>
          Login
        </Link>
      </p>
    </div>
  )
}

export default Register
