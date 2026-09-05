import { useCallback, useEffect, useRef, useState } from "react"
import { Link } from "react-router-dom"
import PropertyCard from "../components/propertyCard"
import { useAuth } from "../context/AuthContext"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import "./properties.css"
import "./favorites.css"
import { apiFetch } from "../utils/apiFetch"

function Favorites() {
  const { logout } = useAuth()
  const [favorites, setFavorites] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState("")
  const [actionError, setActionError] = useState("")
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [removingIds, setRemovingIds] = useState(() => new Set())
  const removingIdsRef = useRef(new Set())

  const fetchFavorites = useCallback(async (signal) => {
    const token = localStorage.getItem("access_token")

    if (!token) {
      setLoadError("Inicie sesión para ver sus favoritos.")
      setLoading(false)
      return
    }

    setLoading(true)
    setLoadError("")

    try {
      const response = await apiFetch(
        "/favorites/",
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          signal,
        }
      )

      const data = await readApiResponse(response)

      if (response.status === 401) {
        logout()
        return
      }

      if (!response.ok) {
        throw new Error(getApiError(data, "No pudimos cargar sus favoritos"))
      }

      setFavorites(data)
    } catch (error) {
      if (error.name !== "AbortError") {
        console.error("Favorites error:", error)
        setLoadError(error.message)
      }
    } finally {
      if (!signal.aborted) setLoading(false)
    }
  }, [logout])

  useEffect(() => {
    const controller = new AbortController()
    const loadTimer = window.setTimeout(() => fetchFavorites(controller.signal), 0)

    return () => {
      window.clearTimeout(loadTimer)
      controller.abort()
    }
  }, [fetchFavorites, loadAttempt])

  async function removeFavorite(propertyId) {
    const token = localStorage.getItem("access_token")
    if (!token || removingIdsRef.current.has(propertyId)) return

    removingIdsRef.current.add(propertyId)
    setRemovingIds((current) => new Set(current).add(propertyId))
    setActionError("")

    try {
      const response = await apiFetch(
        `/favorites/${propertyId}`,
        {
          method: "DELETE",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      if (response.status === 401) {
        logout()
        return
      }

      if (!response.ok) {
        const data = await readApiResponse(response)
        throw new Error(getApiError(data, "No pudimos eliminar el favorito"))
      }

      setFavorites((currentFavorites) =>
        currentFavorites.filter(
          (favorite) => favorite.property.id !== propertyId
        )
      )
    } catch (error) {
      console.error("Remove favorite error:", error)
      setActionError(error.message)
    } finally {
      removingIdsRef.current.delete(propertyId)
      setRemovingIds((current) => {
        const next = new Set(current)
        next.delete(propertyId)
        return next
      })
    }
  }

  if (loading) {
    return <p>Cargando favoritos...</p>
  }

  if (loadError) {
    return (
      <div className="favorites-load-error" role="alert">
        <h1>Favoritos</h1>
        <p>{loadError}</p>
        <button type="button" onClick={() => setLoadAttempt((current) => current + 1)}>
          Intentar de nuevo
        </button>
      </div>
    )
  }

  return (
    <div className="properties-page">
      <div className="properties-header">
        <h1>Mis favoritos</h1>
        <p>Propiedades que ha guardado.</p>
      </div>

      {actionError && <p className="favorites-action-error" role="alert">{actionError}</p>}

      {favorites.length === 0 ? (
        <div>
          <p>Todavía no ha guardado ninguna propiedad.</p>
          <Link to="/">Explorar propiedades</Link>
        </div>
      ) : (
        <div className="properties-grid">
          {favorites.map((favorite) => {
            const property = favorite.property

            return (
              <div className="favorite-listing" key={favorite.id}>
                <PropertyCard
                  id={property.id}
                  title={property.title}
                  location={property.location}
                  bedrooms={property.bedrooms}
                  bathrooms={property.bathrooms}
                  squareFeet={property.square_feet}
                  price={property.price}
                  currency={property.currency}
                  listingType={property.listing_type}
                  propertyType={property.property_type}
                  status={property.status}
                  safetyHold={property.safety_hold}
                  imageUrl={property.image_url}
                  createdAt={property.created_at}
                  updatedAt={property.updated_at}
                />
                <button
                  className="remove-favorite-button"
                  onClick={() => removeFavorite(property.id)}
                  disabled={removingIds.has(property.id)}
                >
                  {removingIds.has(property.id) ? "Eliminando..." : "Eliminar de favoritos"}
                </button>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

export default Favorites
