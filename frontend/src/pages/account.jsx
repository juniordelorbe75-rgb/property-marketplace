import { useCallback, useEffect, useState } from "react"
import { Link, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import "./account.css"
import { apiFetch } from "../utils/apiFetch"
import { getAccountTypeLabel } from "../utils/accountTypes"
import { getSellerCategoryLabel, getSellerRegistrationFields } from "../utils/sellerDetails"
import SellerFields from "../components/SellerFields"

function Account() {
  const navigate = useNavigate()
  const { login, logout } = useAuth()

  const [user, setUser] = useState(null)
  const [sellerDetails, setSellerDetails] = useState({})

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
  const [security, setSecurity] = useState(null)
  const [securityPhone, setSecurityPhone] = useState("")
  const [securityPassword, setSecurityPassword] = useState("")
  const [securityCode, setSecurityCode] = useState("")
  const [securityStep, setSecurityStep] = useState("")
  const [securityBusy, setSecurityBusy] = useState(false)
  const [securityMessage, setSecurityMessage] = useState("")
  const [securityError, setSecurityError] = useState("")

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
      setSellerDetails({ seller_category: data.seller_category || "", seller_phone: data.seller_phone || "", business_name: data.business_name || "" })
      setFirstName(data.first_name || data.name || "")
      setMiddleName(data.middle_name || "")
      setLastName(data.last_name || "")
      setDateOfBirth(data.date_of_birth || "")
      setBio(data.bio || "")
      setPublicProfileEnabled(data.public_profile_enabled === true)
      setPublicNameMode(data.public_name_mode === "full_name" ? "full_name" : "first_name")
      setPublicBioVisible(data.public_bio_visible === true)
      setEmail(data.email)

      const securityResponse = await apiFetch("/auth/security/status", {
        headers: { Authorization: `Bearer ${token}` },
        signal,
      })
      const securityData = await readApiResponse(securityResponse)
      if (!securityResponse.ok) throw new Error(getApiError(securityData, "No pudimos cargar la configuración de seguridad"))
      setSecurity(securityData)
      setSecurityPhone(securityData.phone_number || data.seller_phone || "")

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
            ...(user?.account_type === "seller" && editingProfile ? getSellerRegistrationFields("seller", sellerDetails) : {}),
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
      setSellerDetails({ seller_category: data.seller_category || "", seller_phone: data.seller_phone || "", business_name: data.business_name || "" })
      setFirstName(data.first_name || data.name || "")
      setMiddleName(data.middle_name || "")
      setLastName(data.last_name || "")
      setDateOfBirth(data.date_of_birth || "")
      setBio(data.bio || "")
      setPublicProfileEnabled(data.public_profile_enabled === true)
      setPublicNameMode(data.public_name_mode === "full_name" ? "full_name" : "first_name")
      setPublicBioVisible(data.public_bio_visible === true)
      setEmail(data.email)

      if (!security?.mfa_enabled && data.seller_phone) setSecurityPhone(data.seller_phone)
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

  async function securityRequest(path, body) {
    const response = await apiFetch(path, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${localStorage.getItem("access_token")}`,
        ...(body ? { "Content-Type": "application/json" } : {}),
      },
      ...(body ? { body: JSON.stringify(body) } : {}),
    })
    const data = await readApiResponse(response)
    if (!response.ok) throw new Error(getApiError(data, "No pudimos actualizar la verificación en dos pasos"))
    return data
  }

  async function sendSmsSetup() {
    setSecurityBusy(true)
    setSecurityError("")
    setSecurityMessage("")
    try {
      await securityRequest("/auth/security/sms/setup", { phone: securityPhone })
      setSecurityStep("enable")
      setSecurityMessage("Código enviado. Llegará por SMS y vencerá en 10 minutos.")
    } catch (error) {
      setSecurityError(error.message)
    } finally {
      setSecurityBusy(false)
    }
  }

  async function enableSmsMfa(event) {
    event.preventDefault()
    setSecurityBusy(true)
    setSecurityError("")
    try {
      const data = await securityRequest("/auth/security/sms/enable", { password: securityPassword, code: securityCode })
      login(data.access_token)
      setSecurity((current) => ({ ...current, mfa_enabled: true, mfa_method: "sms", phone_number: securityPhone, phone_verified: true }))
      setSecurityStep("")
      setSecurityPassword("")
      setSecurityCode("")
      setSecurityMessage(data.message)
    } catch (error) {
      setSecurityError(error.message)
    } finally {
      setSecurityBusy(false)
    }
  }

  async function sendSmsDisable() {
    setSecurityBusy(true)
    setSecurityError("")
    setSecurityMessage("")
    try {
      await securityRequest("/auth/security/sms/disable/request")
      setSecurityStep("disable")
      setSecurityMessage("Código enviado al teléfono protegido. Escríbalo para confirmar.")
    } catch (error) {
      setSecurityError(error.message)
    } finally {
      setSecurityBusy(false)
    }
  }

  async function disableSmsMfa(event) {
    event.preventDefault()
    setSecurityBusy(true)
    setSecurityError("")
    try {
      const data = await securityRequest("/auth/security/sms/disable", { password: securityPassword, code: securityCode })
      login(data.access_token)
      setSecurity((current) => ({ ...current, mfa_enabled: false, mfa_method: null }))
      setSecurityStep("")
      setSecurityPassword("")
      setSecurityCode("")
      setSecurityMessage(data.message)
    } catch (error) {
      setSecurityError(error.message)
    } finally {
      setSecurityBusy(false)
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

          <span className="account-eyebrow">Su espacio en HabitaRD</span>

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
              <div><span className="information-label">Tipo de cuenta</span><span className="information-value">{getAccountTypeLabel(user?.account_type)}</span></div>
              {user?.account_type === "seller" && <>
                <div><span className="information-label">Tipo de vendedor</span><span className="information-value">{getSellerCategoryLabel(user.seller_category)}</span></div>
                <div><span className="information-label">Teléfono de contacto (privado)</span><span className="information-value">{user.seller_phone || "No proporcionado"}</span></div>
                <div><span className="information-label">Empresa</span><span className="information-value">{user.business_name || "No proporcionada"}</span></div>
              </>}
              <div><span className="information-label">Nombre completo</span><span className="information-value">{displayName}</span></div>
              <div><span className="information-label">Fecha de nacimiento</span><span className="information-value">{displayBirthDate}</span></div>
              <div><span className="information-label">Correo electrónico</span><span className="information-value">{email}</span></div>
              <div className="profile-bio-information"><span className="information-label">Acerca de usted</span><span className="information-value profile-bio-value">{bio || "Todavía no ha agregado información."}</span></div>
            </div>
            {!editingPrivacy && <button type="button" className="primary-button" onClick={() => { setProfileMessage(""); setProfileError(""); setEditingProfile(true) }}>Editar perfil</button>}
          </>}

          {editingProfile && <form id="profile-form" onSubmit={handleProfileSubmit}>

            {user?.account_type === "seller" && <SellerFields idPrefix="account" details={sellerDetails} onChange={setSellerDetails} disabled={savingProfile} />}

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
                setSellerDetails({ seller_category: user?.seller_category || "", seller_phone: user?.seller_phone || "", business_name: user?.business_name || "" })
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

        <section className="account-section">
          <h2>Verificación en dos pasos por SMS</h2>
          <p className="section-description">
            Además de su contraseña, HabitaRD solicitará un código enviado a su teléfono cada vez que inicie sesión.
          </p>

          {security?.mfa_enabled ? (
            <div className="security-status-card">
              <span className="security-badge">Activa</span>
              <div><strong>Teléfono protegido</strong><p>{security.phone_number}</p></div>
            </div>
          ) : (
            <div className="form-group security-phone-field">
              <label htmlFor="security-phone">Teléfono móvil con código de país</label>
              <input
                id="security-phone"
                type="tel"
                autoComplete="tel"
                value={securityPhone}
                onChange={(event) => setSecurityPhone(event.target.value)}
                placeholder="+1 809 555 0123"
                disabled={user?.account_type === "seller" || securityBusy}
              />
              {user?.account_type === "seller" && <small>Para cambiar este número, actualice primero el teléfono de vendedor en su perfil.</small>}
            </div>
          )}

          {!security?.sms_available && <p className="profile-confirmation">El envío de SMS debe configurarse en el servidor antes de activar esta opción.</p>}
          {!user?.has_password && <p className="profile-confirmation">Primero cree una contraseña en la sección siguiente.</p>}
          {securityMessage && <p className="success-message" role="status">{securityMessage}</p>}
          {securityError && <p className="error-message" role="alert">{securityError}</p>}

          {!security?.mfa_enabled && securityStep !== "enable" && (
            <button className="primary-button" type="button" onClick={sendSmsSetup} disabled={securityBusy || !security?.sms_available || !user?.has_password || !securityPhone.trim()}>
              {securityBusy ? "Enviando..." : "Enviar código y activar"}
            </button>
          )}

          {security?.mfa_enabled && securityStep !== "disable" && (
            <button className="secondary-button" type="button" onClick={sendSmsDisable} disabled={securityBusy}>
              {securityBusy ? "Enviando..." : "Desactivar con un código"}
            </button>
          )}

          {securityStep && (
            <form className="security-code-form" onSubmit={securityStep === "enable" ? enableSmsMfa : disableSmsMfa}>
              <div className="form-group">
                <label htmlFor="security-code">Código del SMS</label>
                <input id="security-code" inputMode="numeric" autoComplete="one-time-code" value={securityCode} onChange={(event) => setSecurityCode(event.target.value.replace(/\D/g, "").slice(0, 10))} minLength={4} maxLength={10} required />
              </div>
              <div className="form-group">
                <label htmlFor="security-password">Contraseña actual</label>
                <input id="security-password" type="password" autoComplete="current-password" value={securityPassword} onChange={(event) => setSecurityPassword(event.target.value)} maxLength={128} required />
              </div>
              <div className="edit-actions">
                <button className="primary-button" type="submit" disabled={securityBusy || securityCode.length < 4 || !securityPassword}>{securityBusy ? "Confirmando..." : securityStep === "enable" ? "Activar protección" : "Desactivar protección"}</button>
                <button className="secondary-button" type="button" disabled={securityBusy} onClick={() => { setSecurityStep(""); setSecurityCode(""); setSecurityPassword(""); setSecurityError("") }}>Cancelar</button>
              </div>
            </form>
          )}
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
