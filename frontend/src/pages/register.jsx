import { useState } from "react"
import { useLocation, useNavigate, Link } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { apiFetch } from "../utils/apiFetch"
import { getSafeReturnPath } from "../utils/authRedirect"
import { queueLoginWelcome } from "../utils/loginWelcomeSession"
import PasswordInput from "../components/PasswordInput"
import "./auth.css"

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
  const [confirmPassword, setConfirmPassword] = useState("")

  const [error, setError] = useState("")
  const [loading, setLoading] = useState(false)

  async function handleRegister(event) {
    event.preventDefault()

    setError("")

    if (password !== confirmPassword) {
      setError("Passwords do not match.")
      return
    }

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
    queueLoginWelcome("new")

    navigate(returnTo, { replace: true })

    } catch (error) {
      console.error("Registration error:", error)
      setError(error.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="auth-page">
      <section className="auth-card auth-card-wide">
      <h1>Create Account</h1>

      <p className="auth-intro">Register for your property marketplace account.</p>

      <form className="auth-form" onSubmit={handleRegister}>

        <div className="auth-field">
          <label htmlFor="register-first-name">First name</label>

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

        <div className="auth-field">
          <label htmlFor="register-middle-name">Middle name <span>(optional)</span></label>
          <input id="register-middle-name" type="text" value={middleName} onChange={(event) => setMiddleName(event.target.value)} autoComplete="additional-name" maxLength={100} />
        </div>

        <div className="auth-field">
          <label htmlFor="register-last-name">Last name</label>
          <input id="register-last-name" type="text" value={lastName} onChange={(event) => setLastName(event.target.value)} autoComplete="family-name" maxLength={100} required />
        </div>

        <div className="auth-field">
          <label htmlFor="register-date-of-birth">Date of birth</label>
          <input id="register-date-of-birth" type="date" value={dateOfBirth} onChange={(event) => setDateOfBirth(event.target.value)} max={new Date().toISOString().slice(0, 10)} autoComplete="bday" required />
        </div>

        <div className="auth-field">
          <label htmlFor="register-bio">About you <span>(optional)</span></label>
          <textarea id="register-bio" value={bio} onChange={(event) => setBio(event.target.value)} maxLength={1000} rows={5} placeholder="Tell other marketplace members a little about yourself." />
          <small>{bio.length}/1000 characters</small>
        </div>

        <div className="auth-field">
          <label htmlFor="register-email">Email</label>

          <input
            id="register-email"
            type="email"
            autoComplete="email"
            value={email}
            onChange={(event) =>
              setEmail(event.target.value)
            }
            required
          />
        </div>

        <PasswordInput
          id="register-password"
          label="Password"
          value={password}
          onChange={(event) => setPassword(event.target.value)}
          autoComplete="new-password"
          describedBy="new-password-help"
          minLength={8}
        />
        <small id="new-password-help" className="password-help">Use at least 8 characters. A password manager can create and save a unique password for you.</small>

        <div>
          <PasswordInput
            id="register-confirm-password"
            label="Confirm password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            autoComplete="new-password"
            minLength={8}
            invalid={Boolean(confirmPassword) && password !== confirmPassword}
            describedBy="confirm-password-help"
          />
          <small id="confirm-password-help">
            {confirmPassword && password !== confirmPassword
              ? "Passwords do not match."
              : "Enter the same password again."}
          </small>
        </div>

        {error && <p className="auth-error" role="alert">{error}</p>}

        <button
          type="submit"
          className="auth-submit"
          disabled={loading || !confirmPassword || password !== confirmPassword}
        >
          {loading
            ? "Creating Account..."
            : "Create Account"}
        </button>

      </form>

      <p className="auth-switch">
        Already have an account?{" "}
        <Link to="/login" state={{ returnTo }}>
          Login
        </Link>
      </p>
      </section>
    </main>
  )
}

export default Register
