import { Link } from "react-router-dom"
import PropertyImage from "./PropertyImage"
import { getListingFreshness } from "../utils/listingDate"
import { formatPropertyPrice } from "../utils/propertyPrice"
import { formatPropertyReference } from "../utils/propertyReference"
import "./PropertyCard.css"

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
  imageUrl,
  createdAt,
  updatedAt,
  isFavorite = false,
  favoriteLoading = false,
  onToggleFavorite,
}) {
  const freshness = getListingFreshness(createdAt, updatedAt)

  return (
    <div className="property-card">

      <div className="property-image">
        <PropertyImage imageUrl={imageUrl} title={title} />
        {onToggleFavorite && (
          <button
            type="button"
            className={`property-card-favorite${isFavorite ? " active" : ""}`}
            onClick={() => onToggleFavorite(id)}
            disabled={favoriteLoading}
            aria-pressed={isFavorite}
            aria-label={`${isFavorite ? "Remove" : "Save"} ${title} ${isFavorite ? "from" : "to"} favorites`}
          >
            {favoriteLoading ? "…" : isFavorite ? "♥" : "♡"}
          </button>
        )}
      </div>

      <div className="property-card-content">

        <div className="property-listing-type">
          {listingType === "rent" ? "For Rent" : "For Sale"}
        </div>

        <div
          className={`property-status ${
            status === "available"
              ? "property-status-available"
              : "property-status-unavailable"
          }`}
        >
          {status === "available"
            ? "Available"
            : "Unavailable"}
        </div>

        <h2>{title}</h2>

        <p className="property-reference">{formatPropertyReference(id)}</p>

        <p className="property-location">
          📍 {location}
        </p>

        {freshness && <p className="property-freshness">{freshness}</p>}

        <div className="property-card-info">
          <span>🛏 {bedrooms} Bedrooms</span>
          <span>🛁 {bathrooms} Bathrooms</span>
          {squareFeet > 0 && (
            <span>📐 {Number(squareFeet).toLocaleString()} sq ft</span>
          )}
          <span>🏠 {propertyType}</span>
        </div>

        <div className="property-card-bottom">
          <strong>
            {formatPropertyPrice(price, currency, listingType)}
          </strong>

          <Link to={`/properties/${id}`}>
            View Property →
          </Link>
        </div>

      </div>
    </div>
  )
}

export default PropertyCard
