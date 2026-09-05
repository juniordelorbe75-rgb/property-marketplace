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
  const [publicProfileEnabled, setPublicProfileEnabled] = useState(false)
  const [publicNameMode, setPublicNameMode] = useState("first_name")
  const [publicBioVisible, setPublicBioVisible] = useState(false)
  const [editingProfile, setEditingProfile] = useState(false)
  const [editingPrivacy, setEditingPrivacy] = useState(false)
  const [email, setEmail] = useState("")
  const [profilePassword, setProfilePassword] = useState("")

  const [currentPassword, setCurrentPassword] = useState("")
  const [newPassword, setNewPassword] = useState("")
  const [confirmNewPassword, setConfirmNewPassword] = useState("")
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
  const [verificationMessage, setVerificationMessage] = useState("")
  const [sendingVerification, setSendingVerification] = useState(false)

  const displayName = [firstName, middleName, lastName].filter(Boolean).join(" ") || user?.name || "No proporcionado"
  const displayBirthDate = dateOfBirth
    ? new Intl.DateTimeFormat(undefined, {
        year: "numeric",
        month: "long",
        day: "numeric",
        timeZone: "UTC",
      }).format(new Date(`${dateOfBirth}T00:00:00Z`))
    : "No proporcionada"

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
          getApiError(data, "No pudimos cargar la cuenta")
        )
      }

      setUser(data)
      setFirstName(data.first_name || data.name || "")
      setMiddleName(data.middle_name || "")
      setLastName(data.last_name || "")
      setDateOfBirth(data.date_of_birth || "")
      setBio(data.bio || "")
      setPublicProfileEnabled(data.public_profile_enabled === true)
      setPublicNameMode(data.public_name_mode === "full_name" ? "full_name" : "first_name")
      setPublicBioVisible(data.public_bio_visible === true)
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
        "No pudimos cargar su cuenta. Inténtelo nuevamente en unos momentos."
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

  async function resendVerification() {
    setSendingVerification(true)
    setVerificationMessage("")
    try {
      const response = await apiFetch("/users/email-verification/request", {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
      })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "No pudimos enviar el correo de verificación"))
      setVerificationMessage("Enlace de verificación enviado. Revise su bandeja de entrada y la carpeta de correo no deseado.")
    } catch (error) {
      setVerificationMessage(error.message)
    } finally {
      setSendingVerification(false)
    }
  }

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
            public_profile_enabled: publicProfileEnabled,
            public_name_mode: publicNameMode,
            public_bio_visible: publicBioVisible,
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
          getApiError(data, "No pudimos actualizar el perfil")
        )
      }

      if (data.access_token) {
        login(data.access_token)
      }
      setUser(data)
      setFirstName(data.first_name || data.name || "")
      setMiddleName(data.middle_name || "")
      setLastName(data.last_name || "")
      setDateOfBirth(data.date_of_birth || "")
      setBio(data.bio || "")
      setPublicProfileEnabled(data.public_profile_enabled === true)
      setPublicNameMode(data.public_name_mode === "full_name" ? "full_name" : "first_name")
      setPublicBioVisible(data.public_bio_visible === true)
      setEmail(data.email)
      setProfilePassword("")

      setProfileMessage(
        "Perfil actualizado correctamente."
      )
      setEditingProfile(false)
      setEditingPrivacy(false)

    } catch (error) {
      console.error("Profile update error:", error)
      setProfileError(error.message)
    } finally {
      setSavingProfile(false)
    }
  }

  async function handlePasswordSubmit(event) {
    event.preventDefault()

    if (newPassword !== confirmNewPassword) {
      setPasswordMessage("")
      setPasswordError("Las contraseñas nuevas no coinciden.")
      return
    }

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
            ...(user?.has_password ? { current_password: currentPassword } : {}),
            new_password: newPassword,
          }),
        }
      )

      const data = await readApiResponse(response)

      if (!response.ok) {
        throw new Error(
          getApiError(data, "No pudimos cambiar la contraseña")
        )
      }

      setCurrentPassword("")
      setNewPassword("")
      setConfirmNewPassword("")
      login(data.access_token)
      setUser((current) => ({ ...current, has_password: true }))

      setPasswordMessage(
        "Contraseña cambiada correctamente."
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

    if (deletionConfirmation !== "ELIMINAR") {
      setDeleteError("Escriba ELIMINAR exactamente para confirmar la eliminación de la cuenta.")
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
          getApiError(data, "No pudimos eliminar la cuenta")
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
          <p>Cargando la cuenta...</p>
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
            Intentar de nuevo
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="account-page">

      <div className="account-container">

        <div className="account-header">

          <h1>Mi cuenta</h1>

          <p>
            Administre su perfil, privacidad y seguridad.
          </p>

        </div>

        {profileMessage && <p className="success-message">{profileMessage}</p>}

        {!user?.email_verified && <section className="email-verification-notice" aria-labelledby="verify-email-heading">
          <div>
            <h2 id="verify-email-heading">Verifique su correo</h2>
            <p>Verifique {user?.email} para confirmar que este medio de contacto le pertenece.</p>
            {verificationMessage && <p role="status">{verificationMessage}</p>}
          </div>
          <button type="button" className="primary-button" onClick={resendVerification} disabled={sendingVerification}>
            {sendingVerification ? "Enviando…" : "Reenviar verificación"}
          </button>
        </section>}

        {/* PROFILE */}

        <section className="account-section">

          <h2>Perfil</h2>

          <p className="section-description">Revise su información personal. Los datos solamente podrán modificarse cuando elija editarlos.</p>

          {!editingProfile && <>
            <div className="account-information profile-summary">
              <div><span className="information-label">Nombre completo</span><span className="information-value">{displayName}</span></div>
              <div><span className="information-label">Fecha de nacimiento</span><span className="information-value">{displayBirthDate}</span></div>
              <div><span className="information-label">Correo electrónico</span><span className="information-value">{email}</span></div>
              <div className="profile-bio-information"><span className="information-label">Acerca de usted</span><span className="information-value profile-bio-value">{bio || "Todavía no ha agregado información."}</span></div>
            </div>
            {!editingPrivacy && <button type="button" className="primary-button" onClick={() => { setProfileMessage(""); setProfileError(""); setEditingProfile(true) }}>Editar perfil</button>}
          </>}

          {editingProfile && <form id="profile-form" onSubmit={handleProfileSubmit}>

            <div className="form-group">
              <label htmlFor="first-name">Nombre</label>
              <input id="first-name" type="text" value={firstName} onChange={(event) => setFirstName(event.target.value)} autoComplete="given-name" maxLength={100} required />
            </div>

            <div className="form-group">
              <label htmlFor="middle-name">Segundo nombre <span>(opcional)</span></label>
              <input id="middle-name" type="text" value={middleName} onChange={(event) => setMiddleName(event.target.value)} autoComplete="additional-name" maxLength={100} />
            </div>

            <div className="form-group">
              <label htmlFor="last-name">Apellido</label>
              <input id="last-name" type="text" value={lastName} onChange={(event) => setLastName(event.target.value)} autoComplete="family-name" maxLength={100} required />
            </div>

            <div className="form-group">
              <label htmlFor="date-of-birth">Fecha de nacimiento</label>
              <input id="date-of-birth" type="date" value={dateOfBirth} onChange={(event) => setDateOfBirth(event.target.value)} max={new Date().toISOString().slice(0, 10)} autoComplete="bday" required />
            </div>

            <div className="form-group">
              <label htmlFor="bio">Acerca de usted <span>(opcional)</span></label>
              <textarea id="bio" value={bio} onChange={(event) => setBio(event.target.value)} maxLength={1000} rows={5} placeholder="Comparta una breve presentación con otros miembros de HabitaRD." />
              <small>{bio.length}/1000 caracteres</small>
            </div>

            <div className="form-group">

              <label htmlFor="email">
                Correo electrónico
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
                  Contraseña actual
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
                  Necesaria porque cambiar el correo modifica la forma de iniciar sesión.
                </small>
              </div>
            )}

            {profileError && (
              <p className="error-message">
                {profileError}
              </p>
            )}

            <div className="edit-actions">
              <button type="submit" className="primary-button" disabled={savingProfile || (email.trim().toLowerCase() !== user?.email && !profilePassword)}>{savingProfile ? "Guardando..." : "Guardar cambios"}</button>
              <button type="button" className="secondary-button" disabled={savingProfile} onClick={() => {
                setFirstName(user?.first_name || user?.name || "")
                setMiddleName(user?.middle_name || "")
                setLastName(user?.last_name || "")
                setDateOfBirth(user?.date_of_birth || "")
                setBio(user?.bio || "")
                setEmail(user?.email || "")
                setProfilePassword("")
                setProfileError("")
                setEditingProfile(false)
              }}>Cancelar</button>
            </div>

          </form>}

        </section>

        <section className="account-section">
          <h2>Privacidad del perfil</h2>
          <p className="section-description">
            Su correo y fecha de nacimiento siempre son privados. Elija si otras personas pueden abrir su perfil y qué información podrán ver.
          </p>

          {!editingPrivacy && <div className="account-information privacy-summary">
            <div><span className="information-label">Visibilidad del perfil</span><span className="information-value">{user?.public_profile_enabled ? "Público" : "Privado"}</span></div>
            <div><span className="information-label">Nombre público</span><span className="information-value">{user?.public_name_mode === "full_name" ? "Nombre completo" : "Solo el primer nombre"}</span></div>
            <div><span className="information-label">Presentación</span><span className="information-value">{user?.public_bio_visible ? "Compartida" : "Oculta"}</span></div>
          </div>}

          {!editingPrivacy && !editingProfile && <div className="edit-actions">
            <button type="button" className="primary-button" onClick={() => { setProfileMessage(""); setEditingPrivacy(true) }}>Cambiar privacidad</button>
            {user?.public_profile_enabled && user?.id && <Link className="secondary-button profile-preview-link" to={`/profiles/${user.id}`}>Ver perfil público</Link>}
          </div>}

          {editingPrivacy && <div className="privacy-controls">
            <label className="privacy-option">
              <input type="checkbox" checked={publicProfileEnabled} onChange={(event) => setPublicProfileEnabled(event.target.checked)} />
              <span><strong>Permitir que otras personas vean mi perfil</strong><small>Está desactivado inicialmente. Mientras permanezca así, no habrá un perfil público disponible.</small></span>
            </label>

            <div className="form-group">
              <label htmlFor="public-name-mode">Nombre mostrado públicamente</label>
              <select id="public-name-mode" value={publicNameMode} onChange={(event) => setPublicNameMode(event.target.value)} disabled={!publicProfileEnabled}>
                <option value="first_name">Solo el primer nombre</option>
                <option value="full_name">Nombre completo</option>
              </select>
            </div>

            <label className="privacy-option">
              <input type="checkbox" checked={publicBioVisible} onChange={(event) => setPublicBioVisible(event.target.checked)} disabled={!publicProfileEnabled || !bio} />
              <span><strong>Mostrar mi presentación</strong><small>Su presentación permanecerá oculta hasta que active esta opción.</small></span>
            </label>

            <div className="edit-actions">
              <button className="primary-button" type="button" disabled={savingProfile} onClick={handleProfileSubmit}>{savingProfile ? "Guardando…" : "Guardar preferencias"}</button>
              <button className="secondary-button" type="button" disabled={savingProfile} onClick={() => {
                setPublicProfileEnabled(user?.public_profile_enabled === true)
                setPublicNameMode(user?.public_name_mode === "full_name" ? "full_name" : "first_name")
                setPublicBioVisible(user?.public_bio_visible === true)
                setEditingPrivacy(false)
              }}>Cancelar</button>
            </div>
          </div>}
        </section>

        {/* ACCOUNT INFORMATION */}

        <section className="account-section">

          <h2>Información de la cuenta</h2>

          <div className="account-information">

            <div>
              <span className="information-label">
                Identificador de la cuenta
              </span>

              <span className="information-value">
                #{user?.id}
              </span>
            </div>

            <div>
              <span className="information-label">
                Seguridad de HabitaRD
              </span>

              <Link className="information-value information-link" to="/my-reports">
                Ver mis reportes de seguridad
              </Link>
            </div>

          </div>

        </section>

        {/* PASSWORD */}

        <section className="account-section">

          <h2>{user?.has_password ? "Seguridad" : "Crear una contraseña para la cuenta"}</h2>

          <p className="section-description">
            {user?.has_password
              ? "Cambie su contraseña para proteger la cuenta. Esto cerrará las sesiones abiertas en otros dispositivos."
              : "Su acceso social está activo. Cree una contraseña de HabitaRD para las acciones protegidas de la cuenta."}
          </p>

          <form onSubmit={handlePasswordSubmit}>

            {user?.has_password && <div className="form-group">

              <label htmlFor="current-password">
                Contraseña actual
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

            </div>}

            <div className="form-group">

              <label htmlFor="new-password">
                Contraseña nueva
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
                La contraseña debe tener al menos 8 caracteres.
              </small>

            </div>

            <div className="form-group">
              <label htmlFor="confirm-new-password">Confirmar contraseña nueva</label>
              <input id="confirm-new-password" type="password" value={confirmNewPassword} onChange={(event) => setConfirmNewPassword(event.target.value)} minLength="8" maxLength="128" autoComplete="new-password" required />
              {confirmNewPassword && newPassword !== confirmNewPassword && <small className="password-mismatch">Las contraseñas no coinciden.</small>}
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
              disabled={changingPassword || !confirmNewPassword || newPassword !== confirmNewPassword}
            >
              {changingPassword
                ? "Cambiando..."
                : user?.has_password ? "Cambiar contraseña" : "Crear contraseña"}
            </button>

          </form>

        </section>

        {/* DELETE ACCOUNT */}

        <section className="account-section danger-section">

          <h2>Zona de peligro</h2>

          <p className="section-description">
            Elimine permanentemente su cuenta, propiedades, fotos, favoritos y consultas. Esta acción no se puede deshacer.
          </p>

          {deleteError && (
            <p className="error-message">
              {deleteError}
            </p>
          )}

          {!user?.has_password && <p className="profile-confirmation">Cree una contraseña en la sección Seguridad antes de eliminar esta cuenta.</p>}

          {user?.has_password && <form className="account-deletion-form" onSubmit={handleDeleteAccount}>
            <label>
              <span>Contraseña actual</span>
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
              <span>Escriba ELIMINAR para confirmar</span>
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
              disabled={deletingAccount || !deletionPassword || deletionConfirmation !== "ELIMINAR"}
            >
              {deletingAccount ? "Eliminando..." : "Eliminar cuenta permanentemente"}
            </button>
          </form>}

        </section>

      </div>

    </div>
  )
}

export default Account
