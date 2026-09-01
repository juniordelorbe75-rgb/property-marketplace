import { useEffect, useRef, useState } from "react"
import { useSearchParams } from "react-router-dom"
import "./properties.css"
import PropertyCard from "../components/propertyCard"
import { getApiError } from "../utils/apiError"
import { PROPERTY_AMENITIES } from "../utils/propertyOptions"
import { readApiResponse } from "../utils/apiResponse"
import { apiFetch } from "../utils/apiFetch"
import {
  buildPropertySearchParams,
  getPropertyApiSearchParams,
  readPropertySearchParams,
} from "../utils/propertySearchParams"
import { clearRecentlyViewed, readRecentlyViewed } from "../utils/recentlyViewed"
import { useAuth } from "../context/AuthContext"
import { updateFavoriteIds } from "../utils/favoriteIds"
import {
  readSavedPropertySearches,
  removeSavedPropertySearch,
  savePropertySearch,
} from "../utils/savedPropertySearches"
import { shareSearchPage } from "../utils/searchPageShare"
import DominicanLocationSuggestions from "../components/DominicanLocationSuggestions"

const PROPERTIES_PER_PAGE = 9

function Properties() {
  const { token } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialSearch = readPropertySearchParams(searchParams)
  const [properties, setProperties] = useState([])
  const [recentlyViewed, setRecentlyViewed] = useState(() => readRecentlyViewed())
  const [savedSearches, setSavedSearches] = useState(() => readSavedPropertySearches())
  const [savedSearchMessage, setSavedSearchMessage] = useState("")
  const [favoritePropertyIds, setFavoritePropertyIds] = useState(() => new Set())
  const [favoritePendingIds, setFavoritePendingIds] = useState(() => new Set())
  const favoritePendingIdsRef = useRef(new Set())
  const [currentUserId, setCurrentUserId] = useState(null)
  const [favoriteMessage, setFavoriteMessage] = useState("")
  const [pageShareMessage, setPageShareMessage] = useState("")
  const [totalResults, setTotalResults] = useState(0)
  const [currentPage, setCurrentPage] = useState(initialSearch.page)

  const [reference, setReference] = useState(initialSearch.reference)
  const [location, setLocation] = useState(initialSearch.location)
  const [minPrice, setMinPrice] = useState(initialSearch.minPrice)
  const [maxPrice, setMaxPrice] = useState(initialSearch.maxPrice)
  const [currency, setCurrency] = useState(initialSearch.currency)
  const [propertyType, setPropertyType] = useState(initialSearch.propertyType)
  const [listingType, setListingType] = useState(initialSearch.listingType)
  const [amenity, setAmenity] = useState(initialSearch.amenity)
  const [bedrooms, setBedrooms] = useState(initialSearch.bedrooms)
  const [bathrooms, setBathrooms] = useState(initialSearch.bathrooms)
  const [minSquareFeet, setMinSquareFeet] = useState(initialSearch.minSquareFeet)
  const [sortBy, setSortBy] = useState(initialSearch.sortBy)
  const [status, setStatus] = useState(initialSearch.status)

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState("")
  const [loadAttempt, setLoadAttempt] = useState(0)

  useEffect(() => {
    let cancelled = false
    const controller = new AbortController()

    async function loadProperties() {
      setLoading(true)
      setError("")

      try {
        const parsed = readPropertySearchParams(searchParams)
        setReference(parsed.reference)
        setLocation(parsed.location)
        setMinPrice(parsed.minPrice)
        setMaxPrice(parsed.maxPrice)
        setCurrency(parsed.currency)
        setPropertyType(parsed.propertyType)
        setListingType(parsed.listingType)
        setAmenity(parsed.amenity)
        setBedrooms(parsed.bedrooms)
        setBathrooms(parsed.bathrooms)
        setMinSquareFeet(parsed.minSquareFeet)
        setSortBy(parsed.sortBy)
        setStatus(parsed.status)
        setCurrentPage(parsed.page)

        const apiParams = getPropertyApiSearchParams(searchParams)
        const hasFilters = apiParams.size > 0
        apiParams.set("limit", String(PROPERTIES_PER_PAGE))
        apiParams.set("offset", String((parsed.page - 1) * PROPERTIES_PER_PAGE))
        const url = hasFilters
          ? `/properties/search?${apiParams.toString()}`
          : `/properties/?${apiParams.toString()}`
        const response = await apiFetch(url, { signal: controller.signal })
        const data = await readApiResponse(response)

        if (!response.ok) {
          throw new Error(
            getApiError(data, "Failed to load properties")
          )
        }

        if (!cancelled) {
          setProperties(data)
          const totalCount = Number(response.headers.get("x-total-count"))
          const safeTotal = Number.isSafeInteger(totalCount) && totalCount >= 0
            ? totalCount
            : data.length
          setTotalResults(safeTotal)
          const lastPage = Math.max(1, Math.ceil(safeTotal / PROPERTIES_PER_PAGE))
          const safePage = Math.min(parsed.page, lastPage)
          setCurrentPage(safePage)

          if (safePage !== parsed.page) {
            setSearchParams(buildPropertySearchParams(parsed, safePage), { replace: true })
          }
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Properties error:", error)
          setError(error.message)
        }
      } finally {
        if (!cancelled) {
          setLoading(false)
        }
      }
    }

    loadProperties()

    return () => {
      cancelled = true
      controller.abort()
    }
  }, [loadAttempt, searchParams, setSearchParams])

  useEffect(() => {
    let cancelled = false

    async function loadFavoriteState() {
      if (!token) {
        setFavoritePropertyIds(new Set())
        setCurrentUserId(null)
        return
      }

      try {
        const headers = { Authorization: `Bearer ${token}` }
        const [favoritesResponse, profileResponse] = await Promise.all([
          apiFetch("/favorites/", { headers }),
          apiFetch("/users/me", { headers }),
        ])
        const [favorites, profile] = await Promise.all([
          readApiResponse(favoritesResponse),
          readApiResponse(profileResponse),
        ])
        if (!favoritesResponse.ok || !profileResponse.ok) return
        if (!cancelled) {
          setFavoritePropertyIds(new Set(favorites.map((favorite) => favorite.property.id)))
          setCurrentUserId(profile.id)
        }
      } catch (favoriteError) {
        console.error("Favorite state error:", favoriteError)
      }
    }

    loadFavoriteState()
    return () => { cancelled = true }
  }, [token])

  function handleSearch(event) {
    event.preventDefault()
    setSearchParams(buildPropertySearchParams({
      reference, location, minPrice, maxPrice, currency, propertyType, listingType, amenity,
      bedrooms, bathrooms, minSquareFeet, status, sortBy,
    }))
  }

  function handleClearSearch() {
    setReference("")
    setLocation("")
    setMinPrice("")
    setMaxPrice("")
    setCurrency("")
    setPropertyType("")
    setListingType("")
    setAmenity("")
    setBedrooms("")
    setBathrooms("")
    setMinSquareFeet("")
    setStatus("")
    setSortBy("newest")

    setSearchParams({})
  }

  function changePage(page) {
    setSearchParams(buildPropertySearchParams({
      reference, location, minPrice, maxPrice, currency, propertyType, listingType, amenity,
      bedrooms, bathrooms, minSquareFeet, status, sortBy,
    }, page))
    window.scrollTo({ top: 0, behavior: "smooth" })
  }

  function handleSaveSearch() {
    const next = savePropertySearch(localStorage, searchParams)
    setSavedSearches(next)
    setSavedSearchMessage(next.length ? "Search saved on this device." : "Choose at least one filter before saving.")
  }

  function openSavedSearch(query) {
    setSearchParams(new URLSearchParams(query))
    setSavedSearchMessage("")
  }

  function deleteSavedSearch(query) {
    setSavedSearches(removeSavedPropertySearch(localStorage, query))
    setSavedSearchMessage("Saved search removed.")
  }

  async function toggleCardFavorite(propertyId) {
    if (!token || favoritePendingIdsRef.current.has(propertyId)) return

    const isFavorite = favoritePropertyIds.has(propertyId)
    setFavoriteMessage("")
    favoritePendingIdsRef.current.add(propertyId)
    setFavoritePendingIds((current) => updateFavoriteIds(current, propertyId, true))
    try {
      const response = await apiFetch(`/favorites/${propertyId}`, {
        method: isFavorite ? "DELETE" : "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
      if (!response.ok) {
        const data = await readApiResponse(response)
        throw new Error(getApiError(data, "Failed to update favorite"))
      }
      setFavoritePropertyIds((current) => updateFavoriteIds(current, propertyId, !isFavorite))
      setFavoriteMessage(isFavorite ? "Property removed from favorites." : "Property saved to favorites.")
    } catch (favoriteError) {
      console.error("Favorite update error:", favoriteError)
      setFavoriteMessage(favoriteError.message)
    } finally {
      favoritePendingIdsRef.current.delete(propertyId)
      setFavoritePendingIds((current) => updateFavoriteIds(current, propertyId, false))
    }
  }

  async function handleSharePage() {
    const result = await shareSearchPage(navigator, window.location.href)
    if (result.method === "clipboard") {
      setPageShareMessage("Search page link copied.")
    } else if (result.method === "manual") {
      window.prompt("Copy this search page link:", result.url)
      setPageShareMessage("Search page link ready to copy.")
    } else if (result.method === "native") {
      setPageShareMessage("Search page shared.")
    }
  }

  const totalPages = Math.max(
    1,
    Math.ceil(totalResults / PROPERTIES_PER_PAGE)
  )
  const firstPropertyIndex =
    (currentPage - 1) * PROPERTIES_PER_PAGE
  const visibleProperties = properties
  const firstVisibleNumber = totalResults === 0
    ? 0
    : firstPropertyIndex + 1
  const lastVisibleNumber = Math.min(
    firstPropertyIndex + PROPERTIES_PER_PAGE,
    totalResults
  )

  return (
    <div className="properties-page">

      <div className="properties-header">
        <div>
          <h1>Find Your Property</h1>
          <p>Search available properties on the marketplace.</p>
        </div>
        <button type="button" className="share-search-page" onClick={handleSharePage}>
          Share this page
        </button>
      </div>
      {pageShareMessage && <p className="page-share-message" aria-live="polite">{pageShareMessage}</p>}

      <div className="property-search">

        <h2>Search Properties</h2>

        <form onSubmit={handleSearch}>

          <div>
            <label>Listing Reference (optional)</label>

            <input
              type="text"
              list="dominican-location-suggestions"
              value={reference}
              onChange={(event) => setReference(event.target.value)}
              placeholder="PM-000123"
              maxLength="20"
            />
          </div>

          <div>
            <label>Location (optional)</label>

            <input
              type="text"
              value={location}
              onChange={(event) =>
                setLocation(event.target.value)
              }
              placeholder="Santo Domingo, Distrito Nacional"
            />
            <DominicanLocationSuggestions />
          </div>

          <div>
            <label>Currency (optional)</label>

            <select
              value={currency}
              onChange={(event) => {
                const nextCurrency = event.target.value
                setCurrency(nextCurrency)
                if (!nextCurrency) {
                  setMinPrice("")
                  setMaxPrice("")
                  if (sortBy !== "newest") setSortBy("newest")
                }
              }}
            >
              <option value="">Any Currency</option>
              <option value="USD">US Dollars (US$)</option>
              <option value="DOP">Dominican Pesos (RD$)</option>
            </select>
          </div>

          <div>
            <label>Min Price (optional)</label>

            <input
              type="number"
              min="0"
              value={minPrice}
              disabled={!currency}
              onChange={(event) =>
                setMinPrice(event.target.value)
              }
              placeholder="100000"
            />
          </div>

          <div>
            <label>Max Price (optional)</label>

            <input
              type="number"
              min="0"
              value={maxPrice}
              disabled={!currency}
              onChange={(event) =>
                setMaxPrice(event.target.value)
              }
              placeholder="500000"
            />
          </div>

          <div>
            <label>Listing For (optional)</label>

            <select value={listingType} onChange={(event) => setListingType(event.target.value)}>
              <option value="">Sale or Rent</option>
              <option value="sale">For Sale</option>
              <option value="rent">For Rent</option>
            </select>
          </div>

          <div>
            <label>Property Type (optional)</label>

            <select
              value={propertyType}
              onChange={(event) =>
                setPropertyType(event.target.value)
              }
            >
              <option value="">Any Type</option>
              <option value="House">House</option>
              <option value="Villa">Villa</option>
              <option value="Apartment">Apartment</option>
              <option value="Condo">Condo</option>
            </select>
          </div>

          <div>
            <label>Bedrooms (optional)</label>

            <input
              type="number"
              min="0"
              value={bedrooms}
              onChange={(event) =>
                setBedrooms(event.target.value)
              }
              placeholder="2"
            />
          </div>

          <div>
            <label>Amenity (optional)</label>
            <select value={amenity} onChange={(event) => setAmenity(event.target.value)}>
              <option value="">Any Amenity</option>
              {PROPERTY_AMENITIES.map((option) => <option value={option} key={option}>{option}</option>)}
            </select>
          </div>

          <div>
            <label>Bathrooms (optional)</label>

            <input
              type="number"
              min="0"
              max="100"
              value={bathrooms}
              onChange={(event) =>
                setBathrooms(event.target.value)
              }
              placeholder="2"
            />
          </div>

          <div>
            <label>Minimum Square Feet (optional)</label>

            <input
              type="number"
              min="0"
              max="10000000"
              value={minSquareFeet}
              onChange={(event) =>
                setMinSquareFeet(event.target.value)
              }
              placeholder="1200"
            />
          </div>

          <div>
            <label>Status (optional)</label>

            <select
              value={status}
              onChange={(event) =>
                setStatus(event.target.value)
              }
            >
              <option value="">Any Status</option>
              <option value="available">Available</option>
              <option value="unavailable">Unavailable</option>
            </select>
          </div>

          <div>
            <label>Sort Results</label>

            <select
              value={sortBy}
              onChange={(event) =>
                setSortBy(event.target.value)
              }
            >
              <option value="newest">Newest First</option>
              <option value="price_low" disabled={!currency}>Price: Low to High</option>
              <option value="price_high" disabled={!currency}>Price: High to Low</option>
            </select>
          </div>

          <div className="search-actions">
            <button type="submit">
              Search
            </button>

            <button
              type="button"
              className="clear-button"
              onClick={handleClearSearch}
            >
              Clear
            </button>

            <button
              type="button"
              className="save-search-button"
              onClick={handleSaveSearch}
              disabled={!buildPropertySearchParams(readPropertySearchParams(searchParams)).toString()}
            >
              Save search
            </button>
          </div>

        </form>
        {savedSearchMessage && <p className="saved-search-message" aria-live="polite">{savedSearchMessage}</p>}
      </div>

      {savedSearches.length > 0 && (
        <section className="saved-searches" aria-labelledby="saved-searches-title">
          <h2 id="saved-searches-title">Saved Searches</h2>
          <p>Quickly reopen searches saved on this device.</p>
          <div className="saved-search-list">
            {savedSearches.map((savedSearch) => (
              <div className="saved-search-item" key={savedSearch.query}>
                <button type="button" onClick={() => openSavedSearch(savedSearch.query)}>
                  {savedSearch.label}
                </button>
                <button
                  type="button"
                  className="remove-saved-search"
                  onClick={() => deleteSavedSearch(savedSearch.query)}
                  aria-label={`Remove saved search: ${savedSearch.label}`}
                >
                  Remove
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {favoriteMessage && <p className="favorite-card-message" aria-live="polite">{favoriteMessage}</p>}

      {loading && (
        <p>Loading properties...</p>
      )}

      {error && (
        <div className="property-load-error" role="alert">
          <p className="property-error">{error}</p>
          <button type="button" onClick={() => setLoadAttempt((current) => current + 1)}>
            Try again
          </button>
        </div>
      )}

      {!loading && !error && (
        <>

          <h2>
            {totalResults}{" "}
            {totalResults === 1
              ? "Property"
              : "Properties"}{" "}
            Found
          </h2>

          {properties.length > 0 && (
            <p className="results-summary">
              Showing {firstVisibleNumber}–{lastVisibleNumber} of{" "}
              {totalResults}
            </p>
          )}

          {totalResults === 0 ? (
            <div>
              <p>
                No properties match your search.
              </p>
            </div>
          ) : (

            <div className="properties-grid">

              {visibleProperties.map((property) => (
                <PropertyCard
                  key={property.id}
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
                  imageUrl={property.image_url}
                  createdAt={property.created_at}
                  updatedAt={property.updated_at}
                  isFavorite={favoritePropertyIds.has(property.id)}
                  favoriteLoading={favoritePendingIds.has(property.id)}
                  onToggleFavorite={token && Number.isSafeInteger(property.owner_id) && property.owner_id !== currentUserId ? toggleCardFavorite : undefined}
                />
              ))}

            </div>

          )}

          {totalPages > 1 && (
            <nav className="pagination" aria-label="Property results pages">
              <button
                type="button"
                onClick={() => changePage(currentPage - 1)}
                disabled={currentPage === 1}
              >
                Previous
              </button>

              <span aria-current="page">
                Page {currentPage} of {totalPages}
              </span>

              <button
                type="button"
                onClick={() => changePage(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Next
              </button>
            </nav>
          )}

        </>
      )}

      {searchParams.size === 0 && recentlyViewed.length > 0 && (
        <section className="recently-viewed" aria-labelledby="recently-viewed-title">
          <div className="recently-viewed-header">
            <div>
              <h2 id="recently-viewed-title">Recently Viewed</h2>
              <p>Continue exploring properties you viewed on this device.</p>
            </div>
            <button
              type="button"
              onClick={() => {
                clearRecentlyViewed()
                setRecentlyViewed([])
              }}
            >
              Clear history
            </button>
          </div>
          <div className="properties-grid recently-viewed-grid">
            {recentlyViewed.map((property) => (
              <PropertyCard
                key={property.id}
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
                imageUrl={property.image_url}
                createdAt={property.created_at}
                updatedAt={property.updated_at}
                isFavorite={favoritePropertyIds.has(property.id)}
                favoriteLoading={favoritePendingIds.has(property.id)}
                onToggleFavorite={token && Number.isSafeInteger(property.owner_id) && property.owner_id !== currentUserId ? toggleCardFavorite : undefined}
              />
            ))}
          </div>
        </section>
      )}

    </div>
  )
}

export default Properties
