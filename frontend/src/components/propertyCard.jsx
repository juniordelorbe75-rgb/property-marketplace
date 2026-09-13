import { Link } from "react-router-dom"
import PropertyImage from "./PropertyImage"
import { getListingFreshness } from "../utils/listingDate"
import { formatPropertyPrice } from "../utils/propertyPrice"
import { formatPropertyReference } from "../utils/propertyReference"
import "./PropertyCard.css"

const PROPERTY_TYPE_LABELS = {
  House: "Casa",
  Villa: "Villa",
  Apartment: "Apartamento",
  Condo: "Condominio",
}

function PropertyCard({
  id,
  title,
  location,
  bedrooms,
  bathrooms,
  squareFeet,
  price,
  currency,
  listingType,
  propertyType,
  status,
  safetyHold = false,
  imageUrl,
  createdAt,
  updatedAt,
  isFavorite = false,
  favoriteLoading = false,
  onToggleFavorite,
  externalUrl,
  attribution,
  areaSqm,
}) {
  const freshness = getListingFreshness(createdAt, updatedAt)

  return (
    <div className="property-card">

      {externalUrl ? (
        <a
          className="property-card-hit-area"
          href={externalUrl}
          target="_blank"
          rel="noreferrer"
          aria-label={`Ver ${title} en la fuente`}
        />
      ) : (
        <Link
          className="property-card-hit-area"
          to={`/properties/${id}`}
          aria-label={`Ver detalles de ${title}`}
        />
      )}

      <div className="property-image">
        <PropertyImage imageUrl={imageUrl} title={title} />
        {onToggleFavorite && (
          <button
            type="button"
            className={`property-card-favorite${isFavorite ? " active" : ""}`}
            onClick={() => onToggleFavorite(id)}
            disabled={favoriteLoading}
            aria-pressed={isFavorite}
            aria-label={`${isFavorite ? "Quitar" : "Guardar"} ${title} ${isFavorite ? "de" : "en"} favoritos`}
          >
            {favoriteLoading ? "…" : isFavorite ? "♥" : "♡"}
          </button>
        )}
      </div>

      <div className="property-card-content">

        <div className="property-listing-type">
          {listingType === "rent" ? "En alquiler" : "En venta"}
        </div>

        <div
          className={`property-status ${
            safetyHold
              ? "property-status-safety-hold"
              : status === "available"
              ? "property-status-available"
              : "property-status-unavailable"
          }`}
        >
          {safetyHold
            ? "En revisión"
            : status === "available"
            ? "Disponible"
            : "No disponible"}
        </div>

        <h2>{title}</h2>

        {externalUrl ? (
          <p className="property-reference">Anuncio verificado de un aliado</p>
        ) : (
          <p className="property-reference">{formatPropertyReference(id)}</p>
        )}

        <p className="property-location">
          📍 {location}
        </p>

        {freshness && <p className="property-freshness">{freshness}</p>}

        <div className="property-card-info">
          <span>🛏 {bedrooms} habitaciones</span>
          <span>🛁 {bathrooms} baños</span>
          {squareFeet > 0 && (
            <span>📐 {Number(squareFeet).toLocaleString()} pies²</span>
          )}
          {areaSqm > 0 && <span>📐 {Number(areaSqm).toLocaleString()} m²</span>}
          <span>⌂ {PROPERTY_TYPE_LABELS[propertyType] || propertyType}</span>
        </div>

        <div className="property-card-bottom">
          <strong>
            {formatPropertyPrice(price, currency, listingType)}
          </strong>

          {externalUrl ? (
            <a href={externalUrl} target="_blank" rel="noreferrer">Ver en la fuente ↗</a>
          ) : (
            <Link to={`/properties/${id}`}>Ver propiedad →</Link>
          )}
        </div>

        {attribution && <p className="property-attribution">{attribution}</p>}

      </div>
    </div>
  )
}

export default PropertyCard
