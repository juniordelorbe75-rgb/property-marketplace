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
      {loading && <p>Cargando perfil…</p>}
      {!loading && error && <section className="public-profile-card" role="alert"><h1>Perfil no disponible</h1><p>{error}</p><button type="button" onClick={() => setAttempt((value) => value + 1)}>Intentar de nuevo</button><Link to="/">Volver al inicio</Link></section>}
      {!loading && profile && <section className="public-profile-card">
        <p className="public-profile-label">Perfil de HabitaRD</p>
        <h1>{profile.display_name}</h1>
        {profile.bio ? <p className="public-profile-bio">{profile.bio}</p> : <p className="public-profile-empty">Este miembro decidió no compartir una biografía.</p>}
        <div className="public-profile-privacy">El correo electrónico y la fecha de nacimiento son privados y nunca aparecen en perfiles públicos.</div>
        <Link to="/search">Buscar propiedades</Link>
      </section>}
    </main>
  )
}

export default PublicProfile
