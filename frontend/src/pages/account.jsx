import { useCallback, useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import "./account.css"
import { apiFetch } from "../utils/apiFetch"

function Account() {
  const navigate = useNavigate()
  const { login, logout } = useAuth()

  const [user, setUser] = useState(null)

  const [firstName, setFirstName] = useState("")
  const [middleName, setMiddleName] = useState("")
  const [lastName, setLastName] = useState("")
  const [dateOfBirth, setDateOfBirth] = useState("")
  const [bio, setBio] = useState("")
  const [email, setEmail] = useState("")
  const [profilePassword, setProfilePassword] = useState("")

  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [deletionPassword, setDeletionPassword] = useState("")
  const [deletionConfirmation, setDeletionConfirmation] = useState("")

  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [savingProfile, setSavingProfile] = useState(false)
  const [changingPassword, setChangingPassword] = useState(false)
  const [deletingAccount, setDeletingAccount] = useState(false)

  const [profileMessage, setProfileMessage] = useState("")
  const [profileError, setProfileError] = useState("")

  const [passwordMessage, setPasswordMessage] = useState("")
  const [passwordError, setPasswordError] = useState("")

  const [deleteError, setDeleteError] = useState("")

  const displayName = [firstName, middleName, lastName].filter(Boolean).join(" ") || user?.name || "Not provided"
  const displayBirthDate = dateOfBirth
    ? new Intl.DateTimeFormat(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
        timeZone: "UTC",
      }).format(new Date(`${dateOfBirth}T00:00:00Z`))
    : "Not provided"

  const fetchAccount = useCallback(async (signal) => {
    const token = localStorage.getItem("access_token")
    let response

    if (!token) {
      navigate("/login")
      return
    }

    setLoading(true)
    setLoadError("")

    try {
      response = await apiFetch(
        "/users/me",
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          signal,
        }
      )

      const data = await readApiResponse(response)

      if (!response.ok) {
        throw new Error(
          getApiError(data, "Failed to load account")
        )
      }

      setUser(data)
      setFirstName(data.first_name || data.name || "")
      setMiddleName(data.middle_name || "")
      setLastName(data.last_name || "")
      setDateOfBirth(data.date_of_birth || "")
      setBio(data.bio || "")
      setEmail(data.email)

    } catch (error) {
      if (signal.aborted) return

      console.error("Account error:", error)

      if (response?.status === 401) {
        logout()
        navigate("/login")
        return
      }

      setLoadError(
        "Unable to load your account. Check that both app servers are running, then try again."
      )
    } finally {
      if (!signal.aborted) setLoading(false)
    }
  }, [logout, navigate])

  useEffect(() => {
    const controller = new AbortController()
    const loadTimer = window.setTimeout(() => fetchAccount(controller.signal), 0)

    return () => {
      window.clearTimeout(loadTimer)
      controller.abort()
    }
  }, [fetchAccount, loadAttempt])

  async function handleProfileSubmit(event) {
    event.preventDefault()

    const token = localStorage.getItem("access_token")

    if (!token) {
      navigate("/login")
      return
    }

    setSavingProfile(true)
    setProfileMessage("")
    setProfileError("")

    try {
      const response = await apiFetch(
        "/users/me",
        {
          method: "PUT",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            first_name: firstName,
            middle_name: middleName,
            last_name: lastName,
            date_of_birth: dateOfBirth,
            bio,
            email,
            ...(email.trim().toLowerCase() !== user?.email
              ? { current_password: profilePassword }
              : {}),
          }),
        }
      )

      const data = await readApiResponse(response)

      if (!response.ok) {
        throw new Error(
          getApiError(data, "Failed to update profile")
        )
      }

      setUser(data)
      setFirstName(data.first_name || data.name || "")
      setMiddleName(data.middle_name || "")
      setLastName(data.last_name || "")
      setDateOfBirth(data.date_of_birth || "")
      setBio(data.bio || "")
      setEmail(data.email)
      setProfilePassword("")

      setProfileMessage(
        "Profile updated successfully."
      )

    } catch (error) {
      console.error("Profile update error:", error)
      setProfileError(error.message)
    } finally {
      setSavingProfile(false)
    }
  }

  async function handlePasswordSubmit(event) {
    event.preventDefault()

    const token = localStorage.getItem("access_token")

    if (!token) {
      navigate("/login")
      return
    }

    setChangingPassword(true)
    setPasswordMessage("")
    setPasswordError("")

    try {
      const response = await apiFetch(
        "/users/me/password",
        {
          method: "PATCH",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({
            current_password: currentPassword,
            new_password: newPassword,
          }),
        }
      )

      const data = await readApiResponse(response)

      if (!response.ok) {
        throw new Error(
          getApiError(data, "Failed to change password")
        )
      }

      setCurrentPassword("")
      setNewPassword("")
      login(data.access_token)

      setPasswordMessage(
        "Password changed successfully."
      )

    } catch (error) {
      console.error("Password change error:", error)
      setPasswordError(error.message)
    } finally {
      setChangingPassword(false)
    }
  }

  async function handleDeleteAccount(event) {
    event.preventDefault()

    if (deletionConfirmation !== "DELETE") {
      setDeleteError("Type DELETE exactly to confirm account deletion.")
      return
    }

    const token = localStorage.getItem("access_token")

    if (!token) {
      navigate("/login")
      return
    }

    setDeletingAccount(true)
    setDeleteError("")

    try {
      const response = await apiFetch(
        "/users/me",
        {
          method: "DELETE",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
          },
          body: JSON.stringify({ current_password: deletionPassword }),
        }
      )

      const data = await readApiResponse(response)

      if (!response.ok) {
        throw new Error(
          getApiError(data, "Failed to delete account")
        )
      }

      logout()

      navigate("/login")

    } catch (error) {
      console.error("Delete account error:", error)
      setDeleteError(error.message)
      setDeletingAccount(false)
    }
  }

  if (loading) {
    return (
      <div className="account-page">
        <div className="account-container">
          <p>Loading account...</p>
        </div>
      </div>
    )
  }

  if (loadError) {
    return (
      <div className="account-page">
        <div className="account-container">
          <p className="error-message">{loadError}</p>
          <button
            type="button"
            className="primary-button"
            onClick={() => setLoadAttempt((current) => current + 1)}
          >
            Try Again
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="account-page">

      <div className="account-container">

        <div className="account-header">

          <h1>My Account</h1>

          <p>
            Manage your profile and account security.
          </p>

        </div>

        {/* PROFILE */}

        <section className="account-section">

          <h2>Profile</h2>

          <p className="section-description">
            Update your personal information.
          </p>

          <form onSubmit={handleProfileSubmit}>

            <div className="form-group">
              <label htmlFor="first-name">First name</label>
              <input id="first-name" type="text" value={firstName} onChange={(event) => setFirstName(event.target.value)} autoComplete="given-name" maxLength={100} required />
            </div>

            <div className="form-group">
              <label htmlFor="middle-name">Middle name <span>(optional)</span></label>
              <input id="middle-name" type="text" value={middleName} onChange={(event) => setMiddleName(event.target.value)} autoComplete="additional-name" maxLength={100} />
            </div>

            <div className="form-group">
              <label htmlFor="last-name">Last name</label>
              <input id="last-name" type="text" value={lastName} onChange={(event) => setLastName(event.target.value)} autoComplete="family-name" maxLength={100} required />
            </div>

            <div className="form-group">
              <label htmlFor="date-of-birth">Date of birth</label>
              <input id="date-of-birth" type="date" value={dateOfBirth} onChange={(event) => setDateOfBirth(event.target.value)} max={new Date().toISOString().slice(0, 10)} autoComplete="bday" required />
            </div>

            <div className="form-group">
              <label htmlFor="bio">About you <span>(optional)</span></label>
              <textarea id="bio" value={bio} onChange={(event) => setBio(event.target.value)} maxLength={1000} rows={5} placeholder="Tell other marketplace members a little about yourself." />
              <small>{bio.length}/1000 characters</small>
            </div>

            <div className="form-group">

              <label htmlFor="email">
                Email
              </label>

              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) =>
                  setEmail(event.target.value)
                }
                required
              />

            </div>

            {email.trim().toLowerCase() !== user?.email && (
              <div className="form-group profile-confirmation">
                <label htmlFor="profile-current-password">
                  Current Password
                </label>

                <input
                  id="profile-current-password"
                  type="password"
                  value={profilePassword}
                  onChange={(event) => setProfilePassword(event.target.value)}
                  autoComplete="current-password"
                  maxLength={128}
                  required
                />

                <small>
                  Required because changing your email changes how you sign in.
                </small>
              </div>
            )}

            {profileMessage && (
              <p className="success-message">
                {profileMessage}
              </p>
            )}

            {profileError && (
              <p className="error-message">
                {profileError}
              </p>
            )}

            <button
              type="submit"
              className="primary-button"
              disabled={
                savingProfile ||
                (email.trim().toLowerCase() !== user?.email && !profilePassword)
              }
            >
              {savingProfile
                ? "Saving..."
                : "Save Changes"}
            </button>

          </form>

        </section>

        {/* ACCOUNT INFORMATION */}

        <section className="account-section">

          <h2>Account Information</h2>

          <div className="account-information">

            <div>
              <span className="information-label">Full name</span>
              <span className="information-value">{displayName}</span>
            </div>

            <div>
              <span className="information-label">Date of birth</span>
              <span className="information-value">{displayBirthDate}</span>
            </div>

            <div className="profile-bio-information">
              <span className="information-label">About you</span>
              <span className="information-value profile-bio-value">
                {bio || "Nothing added yet."}
              </span>
            </div>

            <div>
              <span className="information-label">
                Account ID
              </span>

              <span className="information-value">
                #{user?.id}
              </span>
            </div>

            <div>
              <span className="information-label">
                Marketplace Safety
              </span>

              <Link className="information-value information-link" to="/my-reports">
                View My Safety Reports
              </Link>
            </div>

          </div>

        </section>

        {/* PASSWORD */}

        <section className="account-section">

          <h2>Security</h2>

          <p className="section-description">
            Change your password to keep your account secure.
          </p>

          <form onSubmit={handlePasswordSubmit}>

            <div className="form-group">

              <label htmlFor="current-password">
                Current Password
              </label>

              <input
                id="current-password"
                type="password"
                value={currentPassword}
                onChange={(event) =>
                  setCurrentPassword(event.target.value)
                }
                required
              />

            </div>

            <div className="form-group">

              <label htmlFor="new-password">
                New Password
              </label>

              <input
                id="new-password"
                type="password"
                value={newPassword}
                onChange={(event) =>
                  setNewPassword(event.target.value)
                }
                minLength="8"
                required
              />

              <small>
                Password must be at least 8 characters.
              </small>

            </div>

            {passwordMessage && (
              <p className="success-message">
                {passwordMessage}
              </p>
            )}

            {passwordError && (
              <p className="error-message">
                {passwordError}
              </p>
            )}

            <button
              type="submit"
              className="primary-button"
              disabled={changingPassword}
            >
              {changingPassword
                ? "Changing..."
                : "Change Password"}
            </button>

          </form>

        </section>

        {/* DELETE ACCOUNT */}

        <section className="account-section danger-section">

          <h2>Danger Zone</h2>

          <p className="section-description">
            Permanently delete your account, listings, pictures, favorites, and inquiries. This cannot be undone.
          </p>

          {deleteError && (
            <p className="error-message">
              {deleteError}
            </p>
          )}

          <form className="account-deletion-form" onSubmit={handleDeleteAccount}>
            <label>
              <span>Current password</span>
              <input
                type="password"
                value={deletionPassword}
                onChange={(event) => setDeletionPassword(event.target.value)}
                autoComplete="current-password"
                required
                maxLength={128}
              />
            </label>
            <label>
              <span>Type DELETE to confirm</span>
              <input
                type="text"
                value={deletionConfirmation}
                onChange={(event) => setDeletionConfirmation(event.target.value)}
                autoComplete="off"
                required
              />
            </label>
            <button
              type="submit"
              className="delete-button"
              disabled={deletingAccount || !deletionPassword || deletionConfirmation !== "DELETE"}
            >
              {deletingAccount ? "Deleting..." : "Permanently Delete Account"}
            </button>
          </form>

        </section>

      </div>

    </div>
  )
}

export default Account
