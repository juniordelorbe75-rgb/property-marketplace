import { useCallback, useEffect, useState } from "react"
import { Link, useParams } from "react-router-dom"
import { apiFetch } from "../utils/apiFetch"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import "./PublicProfile.css"

function PublicProfile() {
  const { id } = useParams()
  const [profile, setProfile] = useState(null)
  const [error, setError] = useState("")
  const [loading, setLoading] = useState(true)
  const [attempt, setAttempt] = useState(0)

  const loadProfile = useCallback(async (signal) => {
    setLoading(true)
    setError("")
    try {
      const response = await apiFetch(`/users/${id}/profile`, { signal })
      const data = await readApiResponse(response)
      if (!response.ok) throw new Error(getApiError(data, "Este perfil no está disponible"))
      setProfile(data)
    } catch (requestError) {
      if (!signal.aborted) setError(requestError.message)
    } finally {
      if (!signal.aborted) setLoading(false)
    }
  }, [id])

  useEffect(() => {
    const controller = new AbortController()
    const loadTimer = window.setTimeout(() => loadProfile(controller.signal), 0)
    return () => {
      window.clearTimeout(loadTimer)
      controller.abort()
    }
  }, [attempt, loadProfile])

  return (
    <main className="public-profile-page">
      {loading && <div className="public-profile-loading" role="status"><span aria-hidden="true">H</span><p>Preparando el perfil…</p></div>}
      {!loading && error && <section className="public-profile-card public-profile-error" role="alert"><span className="public-profile-symbol" aria-hidden="true">⌂</span><h1>Perfil no disponible</h1><p>{error}</p><div className="public-profile-actions"><button type="button" onClick={() => setAttempt((value) => value + 1)}>Intentar de nuevo</button><Link to="/search">Buscar propiedades</Link></div></section>}
      {!loading && profile && <section className="public-profile-card">
        <div className="public-profile-heading">
          <span className="public-profile-avatar" aria-hidden="true">{profile.display_name?.trim()?.charAt(0)?.toUpperCase() || "H"}</span>
          <div>
            <p className="public-profile-label">Perfil público de HabitaRD</p>
            <h1>{profile.display_name}</h1>
            <span className="public-profile-member">Miembro de la comunidad</span>
          </div>
        </div>

        <div className="public-profile-about">
          <h2>Acerca de este miembro</h2>
          {profile.bio ? <p className="public-profile-bio">{profile.bio}</p> : <p className="public-profile-empty">Este miembro ha preferido mantener su presentación en privado.</p>}
        </div>

        <div className="public-profile-privacy"><span aria-hidden="true">✓</span><p><strong>Privacidad protegida</strong> El correo electrónico, teléfono y la información personal no aparecen en este perfil.</p></div>
        <div className="public-profile-actions">
          <Link className="public-profile-primary" to="/search">Explorar propiedades</Link>
          <Link className="public-profile-secondary" to="/">Volver al inicio</Link>
        </div>
      </section>}
    </main>
  )
}

export default PublicProfile
