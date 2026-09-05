import { useEffect, useRef, useState } from "react"
import { Link, useNavigate, useSearchParams } from "react-router-dom"
import "./properties.css"
import PropertyCard from "../components/propertyCard"
import { getApiError } from "../utils/apiError"
import { getPropertyAmenityLabel, PROPERTY_AMENITIES } from "../utils/propertyOptions"
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
import { DOMINICAN_PROVINCES } from "../utils/dominicanLocations"

const PROPERTIES_PER_PAGE = 9

function Properties({ searchMode = false }) {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialSearch = readPropertySearchParams(searchParams)
  const [properties, setProperties] = useState([])
  const [externalProperties, setExternalProperties] = useState([])
  const [externalTotal, setExternalTotal] = useState(0)
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
  const [homeProvince, setHomeProvince] = useState("")

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
            getApiError(data, "No pudimos cargar las propiedades")
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

        try {
          const externalParams = new URLSearchParams(apiParams)
          externalParams.delete("reference")
          externalParams.delete("amenity")
          externalParams.delete("status")
          externalParams.delete("min_square_feet")
          const externalResponse = await apiFetch(`/catalog/external?${externalParams.toString()}`, { signal: controller.signal })
          if (!externalResponse.ok) throw new Error("El inventario de aliados no está disponible temporalmente")
          const externalData = await readApiResponse(externalResponse)
          if (!cancelled) {
            setExternalProperties(externalData)
            const count = Number(externalResponse.headers.get("x-total-count"))
            setExternalTotal(Number.isSafeInteger(count) && count >= 0 ? count : externalData.length)
          }
        } catch (externalError) {
          if (externalError.name !== "AbortError") console.warn("El inventario de aliados no está disponible temporalmente")
          if (!cancelled) {
            setExternalProperties([])
            setExternalTotal(0)
          }
        }
      } catch (error) {
        if (!cancelled) {
          console.error("Error al cargar las propiedades:", error)
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

  function handleProvinceBrowse(event) {
    event.preventDefault()
    if (!homeProvince) return
    navigate(`/search?${new URLSearchParams({ location: homeProvince }).toString()}`)
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
    setSavedSearchMessage(next.length ? "Búsqueda guardada en este dispositivo." : "Seleccione al menos un filtro antes de guardar.")
  }

  function openSavedSearch(query) {
    setSearchParams(new URLSearchParams(query))
    setSavedSearchMessage("")
  }

  function deleteSavedSearch(query) {
    setSavedSearches(removeSavedPropertySearch(localStorage, query))
    setSavedSearchMessage("Búsqueda guardada eliminada.")
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
        throw new Error(getApiError(data, "No pudimos actualizar el favorito"))
      }
      setFavoritePropertyIds((current) => updateFavoriteIds(current, propertyId, !isFavorite))
      setFavoriteMessage(isFavorite ? "Propiedad eliminada de favoritos." : "Propiedad guardada en favoritos.")
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
      setPageShareMessage("Enlace de búsqueda copiado.")
    } else if (result.method === "manual") {
      window.prompt("Copie este enlace de búsqueda:", result.url)
      setPageShareMessage("El enlace de búsqueda está listo para copiarse.")
    } else if (result.method === "native") {
      setPageShareMessage("Página de búsqueda compartida.")
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

      {!searchMode && <section className="home-hero" aria-labelledby="home-hero-title">
        <div className="home-hero-copy">
          <p className="home-hero-eyebrow">Propiedades en venta y alquiler</p>
          <h1 id="home-hero-title">Encuentre su lugar en la República Dominicana.</h1>
          <p className="home-hero-summary">Explore el territorio nacional por provincia y consulte cada anuncio con información clara sobre su procedencia.</p>
          <form className="province-browser" onSubmit={handleProvinceBrowse}>
            <label htmlFor="home-province">¿Dónde desea buscar?</label>
            <div>
              <select id="home-province" value={homeProvince} onChange={(event) => setHomeProvince(event.target.value)} required>
                <option value="">Seleccione una provincia o el Distrito Nacional</option>
                {DOMINICAN_PROVINCES.map((province) => <option value={province} key={province}>{province}</option>)}
              </select>
              <button type="submit" disabled={!homeProvince}>Ver propiedades</button>
            </div>
          </form>
          <div className="home-hero-actions">
            <Link className="hero-search-link" to="/search">Usar búsqueda avanzada</Link>
          </div>
          <ul className="home-hero-assurances" aria-label="Información sobre la búsqueda">
            <li>Todo el territorio nacional</li>
            <li>Sin membresía para explorar</li>
            <li>Fuentes identificadas</li>
          </ul>
        </div>
      </section>}


      {searchMode && <div className="properties-header">
        <div>
          <h1>Buscar propiedades</h1>
          <p>Combine los filtros que prefiera para encontrar mejores resultados.</p>
        </div>
        <button type="button" className="share-search-page" onClick={handleSharePage}>Compartir esta página</button>
      </div>}
      {searchMode && pageShareMessage && <p className="page-share-message" aria-live="polite">{pageShareMessage}</p>}

      {searchMode && <div className="property-search" id="property-search">

        <h2>Buscar propiedades</h2>

        <form onSubmit={handleSearch}>

          <div>
            <label>Referencia del anuncio</label>

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
            <label>Ubicación</label>

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
            <label>Moneda</label>

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
              <option value="">Cualquier moneda</option>
              <option value="USD">Dólares estadounidenses (US$)</option>
              <option value="DOP">Pesos dominicanos (RD$)</option>
            </select>
          </div>

          <div>
            <label>Precio mínimo</label>

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
            <label>Precio máximo</label>

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
            <label>Modalidad</label>

            <select value={listingType} onChange={(event) => setListingType(event.target.value)}>
              <option value="">Venta o alquiler</option>
              <option value="sale">En venta</option>
              <option value="rent">En alquiler</option>
            </select>
          </div>

          <div>
            <label>Tipo de propiedad</label>

            <select
              value={propertyType}
              onChange={(event) =>
                setPropertyType(event.target.value)
              }
            >
              <option value="">Cualquier tipo</option>
              <option value="House">Casa</option>
              <option value="Villa">Villa</option>
              <option value="Apartment">Apartamento</option>
              <option value="Condo">Condominio</option>
            </select>
          </div>

          <div>
            <label>Habitaciones</label>

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
            <label>Amenidad</label>
            <select value={amenity} onChange={(event) => setAmenity(event.target.value)}>
              <option value="">Cualquier amenidad</option>
              {PROPERTY_AMENITIES.map((option) => <option value={option} key={option}>{getPropertyAmenityLabel(option)}</option>)}
            </select>
          </div>

          <div>
            <label>Baños</label>

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
            <label>Pies cuadrados mínimos</label>

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
            <label>Estado</label>

            <select
              value={status}
              onChange={(event) =>
                setStatus(event.target.value)
              }
            >
              <option value="">Cualquier estado</option>
              <option value="available">Disponible</option>
              <option value="unavailable">No disponible</option>
            </select>
          </div>

          <div>
            <label>Ordenar resultados</label>

            <select
              value={sortBy}
              onChange={(event) =>
                setSortBy(event.target.value)
              }
            >
              <option value="newest">Más recientes primero</option>
              <option value="price_low" disabled={!currency}>Precio: menor a mayor</option>
              <option value="price_high" disabled={!currency}>Precio: mayor a menor</option>
            </select>
          </div>

          <div className="search-actions">
            <button type="submit">
              Buscar
            </button>

            <button
              type="button"
              className="clear-button"
              onClick={handleClearSearch}
            >
              Limpiar
            </button>

            <button
              type="button"
              className="save-search-button"
              onClick={handleSaveSearch}
              disabled={!buildPropertySearchParams(readPropertySearchParams(searchParams)).toString()}
            >
              Guardar búsqueda
            </button>
          </div>

        </form>
        {savedSearchMessage && <p className="saved-search-message" aria-live="polite">{savedSearchMessage}</p>}
      </div>}

      {searchMode && savedSearches.length > 0 && (
        <section className="saved-searches" aria-labelledby="saved-searches-title">
          <h2 id="saved-searches-title">Búsquedas guardadas</h2>
          <p>Abra rápidamente las búsquedas guardadas en este dispositivo.</p>
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
                  aria-label={`Eliminar búsqueda guardada: ${savedSearch.label}`}
                >
                  Eliminar
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {favoriteMessage && <p className="favorite-card-message" aria-live="polite">{favoriteMessage}</p>}

      {loading && (
        <p>Cargando propiedades...</p>
      )}

      {error && (
        <div className="property-load-error" role="alert">
          <p className="property-error">{error}</p>
          <button type="button" onClick={() => setLoadAttempt((current) => current + 1)}>
            Intentar de nuevo
          </button>
        </div>
      )}

      {!loading && !error && (
        <>

          {searchMode && <h2>{totalResults} {totalResults === 1 ? "propiedad encontrada" : "propiedades encontradas"}</h2>}

          {!searchMode && totalResults > 0 && <div className="home-catalog-heading">
            <div>
              <p>Disponibles ahora</p>
              <h2>Propiedades para explorar</h2>
            </div>
            <span>{totalResults} {totalResults === 1 ? "propiedad" : "propiedades"}</span>
          </div>}

          {properties.length > 0 && (
            <p className="results-summary">
              Mostrando {firstVisibleNumber}–{lastVisibleNumber} de{" "}
              {totalResults}
            </p>
          )}

          {totalResults === 0 && externalProperties.length === 0 ? (
            <div className="empty-property-results">
              <h3>{searchParams.size ? "Todavía no hay propiedades que coincidan con estos filtros." : "Estamos preparando el inventario."}</h3>
              <p>{searchParams.size ? "Pruebe con una zona más amplia o menos filtros." : "Estamos incorporando fuentes dominicanas verificadas. Ya puede explorar mercados y guardar búsquedas en este dispositivo sin crear una cuenta."}</p>
              {searchParams.size ? (
                <button type="button" onClick={handleClearSearch}>Limpiar filtros</button>
              ) : (
                <Link to="/search">Explorar mercados dominicanos</Link>
              )}
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
                  safetyHold={property.safety_hold}
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
            <nav className="pagination" aria-label="Páginas de resultados de propiedades">
              <button
                type="button"
                onClick={() => changePage(currentPage - 1)}
                disabled={currentPage === 1}
              >
                Anterior
              </button>

              <span aria-current="page">
                Página {currentPage} de {totalPages}
              </span>

              <button
                type="button"
                onClick={() => changePage(currentPage + 1)}
                disabled={currentPage === totalPages}
              >
                Siguiente
              </button>
            </nav>
          )}

        </>
      )}

      {searchParams.size === 0 && recentlyViewed.length > 0 && (
        <section className="recently-viewed" aria-labelledby="recently-viewed-title">
          <div className="recently-viewed-header">
            <div>
              <h2 id="recently-viewed-title">Vistas recientemente</h2>
              <p>Continúe explorando propiedades que vio en este dispositivo.</p>
            </div>
            <button
              type="button"
              onClick={() => {
                clearRecentlyViewed()
                setRecentlyViewed([])
              }}
            >
              Borrar historial
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
                safetyHold={property.safety_hold}
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

      {!loading && !error && externalProperties.length > 0 && (
        <section className="partner-results" aria-labelledby="partner-results-title">
          <div className="partner-results-heading">
            <h2 id="partner-results-title">Inventario de aliados</h2>
            <p>{externalTotal} {externalTotal === 1 ? "anuncio autorizado" : "anuncios autorizados"}. Confirme los detalles y la disponibilidad con la fuente.</p>
          </div>
          <div className="properties-grid">
            {externalProperties.map((property) => (
              <PropertyCard
                key={`external-${property.id}`}
                id={property.id}
                title={property.title}
                location={[property.sector, property.municipality, property.province].filter(Boolean).join(", ")}
                bedrooms={property.bedrooms ?? "—"}
                bathrooms={property.bathrooms ?? "—"}
                areaSqm={property.area_sqm}
                price={property.price}
                currency={property.currency}
                listingType={property.listing_type}
                propertyType={property.property_type}
                status="available"
                imageUrl={property.image_urls?.[0] || ""}
                createdAt={property.source_updated_at}
                updatedAt={property.source_updated_at}
                externalUrl={property.source_url}
                attribution={property.attribution}
              />
            ))}
          </div>
        </section>
      )}

      {!searchMode && <section className="home-benefits" aria-labelledby="home-benefits-title">
        <h2 id="home-benefits-title">Una manera más sencilla de avanzar</h2>
        <ul className="home-confidence-list" aria-label="Beneficios del mercado">
          <li><strong>Explore antes de registrarse</strong><span>Vea anuncios y provincias sin crear una cuenta.</span></li>
          <li><strong>Conozca la fuente</strong><span>El inventario importado conserva su proveedor, fecha de actualización y atribución.</span></li>
          <li><strong>Regístrese cuando lo necesite</strong><span>Cree una cuenta solo cuando quiera guardar, consultar o publicar.</span></li>
        </ul>
      </section>}

      {!searchMode && <section className="home-share" aria-labelledby="home-share-title">
        <div>
          <h2 id="home-share-title">Compartir HabitaRD</h2>
          <p>Una forma sencilla de encontrar, alquilar o vender propiedades en la República Dominicana.</p>
        </div>
        <button type="button" className="share-search-page" onClick={handleSharePage}>Compartir esta página</button>
        {pageShareMessage && <p className="page-share-message" aria-live="polite">{pageShareMessage}</p>}
      </section>}

    </div>
  )
}

export default Properties
