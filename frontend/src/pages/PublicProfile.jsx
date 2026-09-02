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
      if (!response.ok) throw new Error(getApiError(data, "This profile is not available"))
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
      {loading && <p>Loading profile…</p>}
      {!loading && error && <section className="public-profile-card" role="alert"><h1>Profile unavailable</h1><p>{error}</p><button type="button" onClick={() => setAttempt((value) => value + 1)}>Try again</button><Link to="/">Return home</Link></section>}
      {!loading && profile && <section className="public-profile-card">
        <p className="public-profile-label">Marketplace profile</p>
        <h1>{profile.display_name}</h1>
        {profile.bio ? <p className="public-profile-bio">{profile.bio}</p> : <p className="public-profile-empty">This member has chosen not to share a biography.</p>}
        <div className="public-profile-privacy">Email and date of birth are private and are never shown on public profiles.</div>
        <Link to="/search">Search properties</Link>
      </section>}
    </main>
  )
}

export default PublicProfile
