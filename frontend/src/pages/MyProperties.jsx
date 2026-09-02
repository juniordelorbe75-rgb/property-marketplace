import { useEffect, useMemo, useRef, useState } from "react"
import { Link } from "react-router-dom"

import PropertyCard from "../components/propertyCard"
import { useAuth } from "../context/AuthContext"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import "./MyProperties.css"
import { apiFetch } from "../utils/apiFetch"
import { buildPropertyStatusUpdate } from "../utils/propertyStatusUpdate"
import { indexPropertyEngagement } from "../utils/propertyEngagement"
import { formatPropertyReference } from "../utils/propertyReference"
import {
  countSellerListingFilters,
  filterSellerListings,
  SELLER_LISTING_FILTERS,
} from "../utils/sellerListingFilters"


function MyProperties() {
  const { logout } = useAuth()
  const [properties, setProperties] = useState([])
  const [stats, setStats] = useState(null)
  const [engagementByProperty, setEngagementByProperty] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [statusMessage, setStatusMessage] = useState("")
  const [statusError, setStatusError] = useState("")
  const [statusPendingIds, setStatusPendingIds] = useState(() => new Set())
  const [listingQuery, setListingQuery] = useState("")
  const [listingFilter, setListingFilter] = useState("all")
  const statusPendingIdsRef = useRef(new Set())

  const visibleProperties = useMemo(
    () => filterSellerListings(properties, engagementByProperty, listingQuery, listingFilter),
    [properties, engagementByProperty, listingQuery, listingFilter],
  )
  const listingFilterCounts = useMemo(
    () => countSellerListingFilters(properties, engagementByProperty),
    [properties, engagementByProperty],
  )

  useEffect(() => {
    const token = localStorage.getItem("access_token")
    const controller = new AbortController()

    if (!token) {
      return () => controller.abort()
    }

    async function loadMyProperties() {
      setLoading(true)
      setError("")

      try {
        const requestOptions = {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        }
        const [response, statsResponse, engagementResponse] = await Promise.all([
          apiFetch("/properties/my", requestOptions),
          apiFetch("/properties/my/stats", requestOptions),
          apiFetch("/properties/my/engagement", requestOptions),
        ])
        const [data, statsData, engagementData] = await Promise.all([
          readApiResponse(response),
          readApiResponse(statsResponse),
          readApiResponse(engagementResponse),
        ])

        if (response.status === 401 || statsResponse.status === 401 || engagementResponse.status === 401) {
          logout()
          return
        }

        if (!response.ok) {
          throw new Error(
            getApiError(data, "Failed to load properties")
          )
        }

        if (!statsResponse.ok) {
          throw new Error(getApiError(statsData, "Failed to load seller statistics"))
        }
        if (!engagementResponse.ok) {
          throw new Error(getApiError(engagementData, "Failed to load listing engagement"))
        }

        setProperties(data)
        setStats(statsData)
        setEngagementByProperty(indexPropertyEngagement(engagementData))
      } catch (error) {
        if (error.name !== "AbortError") {
          console.error("My properties error:", error)
          setError(error.message)
        }
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    loadMyProperties()

    return () => controller.abort()
  }, [loadAttempt, logout])

  async function toggleAvailability(property) {
    const token = localStorage.getItem("access_token")
    if (!token || statusPendingIdsRef.current.has(property.id)) return
    if (property.safety_hold) {
      setStatusMessage("")
      setStatusError("This listing is on a safety hold. You can correct its details, but only a safety administrator can release it.")
      return
    }

    const nextStatus = property.status === "available" ? "unavailable" : "available"
    statusPendingIdsRef.current.add(property.id)
    setStatusPendingIds((current) => new Set(current).add(property.id))
    setStatusMessage("")
    setStatusError("")

    try {
      const response = await apiFetch(`/properties/${property.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "X-Property-Version": String(property.version),
        },
        body: JSON.stringify(buildPropertyStatusUpdate(property, nextStatus)),
      })
      const data = await readApiResponse(response)

      if (response.status === 401) {
        logout()
        return
      }
      if (!response.ok) {
        throw new Error(getApiError(data, "Failed to update listing availability"))
      }

      setProperties((current) => current.map((item) => item.id === data.id ? data : item))
      setStats((current) => current ? {
        ...current,
        available_listings: current.available_listings + (nextStatus === "available" ? 1 : -1),
        unavailable_listings: current.unavailable_listings + (nextStatus === "unavailable" ? 1 : -1),
      } : current)
      setStatusMessage(
        nextStatus === "available"
          ? `${property.title} is now available.`
          : `${property.title} is now unavailable.`,
      )
    } catch (updateError) {
      console.error("Availability update error:", updateError)
      setStatusError(updateError.message)
    } finally {
      statusPendingIdsRef.current.delete(property.id)
      setStatusPendingIds((current) => {
        const next = new Set(current)
        next.delete(property.id)
        return next
      })
    }
  }

  return (
    <main className="my-properties-page">
      <header className="my-properties-header">
        <div>
          <p className="my-properties-eyebrow">Seller dashboard</p>
          <h1>My Listings</h1>
          <p>Manage the properties you have listed on the marketplace.</p>
        </div>

        <Link className="add-property-link" to="/create-property">
          + Add Property
        </Link>
      </header>

      {loading && (
        <p className="my-properties-message">Loading your properties...</p>
      )}

      {error && (
        <section className="my-properties-error" role="alert">
          <p>{error}</p>
          <button type="button" onClick={() => setLoadAttempt((current) => current + 1)}>
            Try again
          </button>
        </section>
      )}

      {statusMessage && <p className="listing-status-message" aria-live="polite">{statusMessage}</p>}
      {statusError && <p className="my-properties-error" role="alert">{statusError}</p>}

      {!loading && !error && stats && (
        <section className="seller-stats" aria-label="Seller statistics">
          <div><strong>{stats.total_listings}</strong><span>Total listings</span></div>
          <div><strong>{stats.available_listings}</strong><span>Available</span></div>
          <div><strong>{stats.unavailable_listings}</strong><span>Unavailable</span></div>
          <div><strong>{stats.favorites_received}</strong><span>Favorites</span></div>
          <div><strong>{stats.inquiries_received}</strong><span>Inquiries</span></div>
          <div><strong>{stats.pending_inquiries}</strong><span>Pending</span></div>
        </section>
      )}

      {!loading && !error && properties.length === 0 && (
        <section className="my-properties-empty">
          <h2>No listings yet</h2>
          <p>Create your first property listing to start reaching buyers.</p>
          <Link className="add-property-link" to="/create-property">
            Create Your First Listing
          </Link>
        </section>
      )}

      {!loading && !error && properties.length > 0 && (
        <section>
          <div className="listing-tools">
            <label className="listing-search">
              <span>Find one of your listings</span>
              <input
                type="search"
                value={listingQuery}
                onChange={(event) => setListingQuery(event.target.value)}
                placeholder="Title, location, or PM-000123"
              />
            </label>
            <div className="listing-filters" aria-label="Filter your listings">
              {SELLER_LISTING_FILTERS.map((filter) => (
                <button
                  key={filter}
                  type="button"
                  className={listingFilter === filter ? "active" : ""}
                  aria-pressed={listingFilter === filter}
                  onClick={() => setListingFilter(filter)}
                >
                  {filter === "attention" ? "Needs attention" : `${filter.charAt(0).toUpperCase()}${filter.slice(1)}`}
                  <span>{listingFilterCounts[filter]}</span>
                </button>
              ))}
            </div>
          </div>

          <p className="listing-count" aria-live="polite">
            Showing {visibleProperties.length} of {properties.length} {properties.length === 1 ? "listing" : "listings"}
          </p>

          {visibleProperties.length === 0 ? (
            <div className="my-properties-no-results">
              <h2>No matching listings</h2>
              <p>Try another title, location, reference, or status.</p>
              <button type="button" onClick={() => { setListingQuery(""); setListingFilter("all") }}>Clear filters</button>
            </div>
          ) : <div className="my-properties-grid">
            {visibleProperties.map((property) => (
              <div className="my-listing-item" key={property.id}>
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
                <div className="listing-engagement" aria-label={`Engagement for ${property.title}`}>
                  <span>♥ {engagementByProperty[property.id]?.favorites || 0} favorites</span>
                  <span>✉ {engagementByProperty[property.id]?.inquiries || 0} inquiries</span>
                  <span className={engagementByProperty[property.id]?.pending_inquiries ? "needs-attention" : ""}>
                    {engagementByProperty[property.id]?.pending_inquiries || 0} pending
                  </span>
                  {(engagementByProperty[property.id]?.inquiries || 0) > 0 && (
                    <Link to={`/inquiries?property=${formatPropertyReference(property.id)}`}>
                      View inquiries
                    </Link>
                  )}
                </div>
                {property.safety_hold && (
                  <p className="listing-safety-hold" role="status">
                    Safety hold active: hidden from discovery and new inquiries. Open the listing to correct its details.
                  </p>
                )}
                <button
                  type="button"
                  className="listing-status-toggle"
                  onClick={() => toggleAvailability(property)}
                  disabled={statusPendingIds.has(property.id) || property.safety_hold}
                >
                  {property.safety_hold
                    ? "Safety hold active"
                    : statusPendingIds.has(property.id)
                    ? "Updating..."
                    : property.status === "available"
                      ? "Mark unavailable"
                      : "Mark available"}
                </button>
              </div>
            ))}
          </div>}
        </section>
      )}
    </main>
  )
}

export default MyProperties
