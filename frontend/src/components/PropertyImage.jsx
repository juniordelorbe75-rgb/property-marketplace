import { useState } from "react"
import {
  getPropertyImageAlt,
  getUnavailableImageLabel,
} from "../utils/propertyImage"
import "./PropertyImage.css"

function PropertyImage({ imageUrl, title, position, priority = false }) {
  const [failedUrl, setFailedUrl] = useState("")
  const showImage = imageUrl && failedUrl !== imageUrl

  if (!showImage) {
    return (
      <span
        className="property-image-placeholder"
        role="img"
        aria-label={getUnavailableImageLabel(title)}
      >
        <span aria-hidden="true" className="property-image-placeholder-icon">⌂</span>
        <span>Imagen no disponible</span>
      </span>
    )
  }

  return (
    <img
      src={imageUrl}
      alt={getPropertyImageAlt(title, position)}
      loading={priority ? "eager" : "lazy"}
      fetchPriority={priority ? "high" : "auto"}
      decoding="async"
      onError={() => setFailedUrl(imageUrl)}
    />
  )
}

export default PropertyImage
