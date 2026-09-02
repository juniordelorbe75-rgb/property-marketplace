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

  const [firstName, setFirstName] = useState("")
  const [middleName, setMiddleName] = useState("")
  const [lastName, setLastName] = useState("")
  const [dateOfBirth, setDateOfBirth] = useState("")
  const [bio, setBio] = useState("")
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
            first_name: firstName,
            middle_name: middleName,
            last_name: lastName,
            date_of_birth: dateOfBirth,
            bio,
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
          <label htmlFor="register-first-name">First name</label>
          <br />

          <input
            type="text"
            id="register-first-name"
            value={firstName}
            onChange={(event) =>
              setFirstName(event.target.value)
            }
            autoComplete="given-name"
            maxLength={100}
            required
          />
        </div>

        <div>
          <label htmlFor="register-middle-name">Middle name <span>(optional)</span></label>
          <br />
          <input id="register-middle-name" type="text" value={middleName} onChange={(event) => setMiddleName(event.target.value)} autoComplete="additional-name" maxLength={100} />
        </div>

        <div>
          <label htmlFor="register-last-name">Last name</label>
          <br />
          <input id="register-last-name" type="text" value={lastName} onChange={(event) => setLastName(event.target.value)} autoComplete="family-name" maxLength={100} required />
        </div>

        <div>
          <label htmlFor="register-date-of-birth">Date of birth</label>
          <br />
          <input id="register-date-of-birth" type="date" value={dateOfBirth} onChange={(event) => setDateOfBirth(event.target.value)} max={new Date().toISOString().slice(0, 10)} autoComplete="bday" required />
        </div>

        <div>
          <label htmlFor="register-bio">About you <span>(optional)</span></label>
          <br />
          <textarea id="register-bio" value={bio} onChange={(event) => setBio(event.target.value)} maxLength={1000} rows={5} placeholder="Tell other marketplace members a little about yourself." />
          <small>{bio.length}/1000 characters</small>
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
