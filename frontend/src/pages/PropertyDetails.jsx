import { useCallback, useEffect, useRef, useState } from "react"
import { Link, useLocation, useNavigate, useParams } from "react-router-dom"
import PropertyImage from "../components/PropertyImage"
import { getApiError } from "../utils/apiError"
import { readApiResponse } from "../utils/apiResponse"
import { PROPERTY_AMENITIES } from "../utils/propertyOptions"
import "./PropertyDetails.css"
import { apiFetch } from "../utils/apiFetch"
import { getReturnPath } from "../utils/authRedirect"
import { rememberRecentlyViewed } from "../utils/recentlyViewed"
import { shareProperty } from "../utils/propertyShare"
import { getListingFreshness } from "../utils/listingDate"
import { formatPropertyPrice } from "../utils/propertyPrice"
import { formatPropertyReference } from "../utils/propertyReference"
import DominicanLocationSuggestions from "../components/DominicanLocationSuggestions"
import { buildPropertyMapUrl, isMapLocationDetailed } from "../utils/propertyMap"
import {
  getAdjacentImage,
  moveImageToCover,
  removeImageAt,
} from "../utils/imageOrder"
import { getDraftOwnerId } from "../utils/listingDraft"
import {
  clearContactInquiryDraft,
  readContactInquiryDraft,
  saveContactInquiryDraft,
} from "../utils/contactInquiryDraft"

const INQUIRY_PROMPTS = [
  "Is this property still available?",
  "I would like to schedule a viewing.",
  "Could you share more details about this property?",
]

function PropertyDetails() {
  const { id } = useParams()
  const inquiryDraftOwnerId = getDraftOwnerId(localStorage.getItem("access_token"))
  const navigate = useNavigate()
  const routeLocation = useLocation()

  const [property, setProperty] = useState(null)
  const [activeImageUrl, setActiveImageUrl] = useState("")
  const [loading, setLoading] = useState(true)
  const [propertyLoadAttempt, setPropertyLoadAttempt] = useState(0)

  const [editing, setEditing] = useState(false)

  const [title, setTitle] = useState("")
  const [description, setDescription] = useState("")
  const [imageUrl, setImageUrl] = useState("")
  const [imageUrls, setImageUrls] = useState([])
  const [imageFiles, setImageFiles] = useState([])
  const [imagePreviews, setImagePreviews] = useState([])
  const imagePreviewsRef = useRef([])
  const [newImagesAreCover, setNewImagesAreCover] = useState(false)
  const [updateLoading, setUpdateLoading] = useState(false)
  const [deleteLoading, setDeleteLoading] = useState(false)
  const [price, setPrice] = useState("")
  const [currency, setCurrency] = useState("USD")
  const [listingType, setListingType] = useState("sale")
  const [amenities, setAmenities] = useState([])
  const [location, setLocation] = useState("")
  const [propertyType, setPropertyType] = useState("")
  const [bedrooms, setBedrooms] = useState("")
  const [bathrooms, setBathrooms] = useState("")
  const [squareFeet, setSquareFeet] = useState("")
  const [status, setStatus] = useState("")

  const [error, setError] = useState("")
  const [showInquiry, setShowInquiry] = useState(false)
  const [inquiryMessage, setInquiryMessage] = useState(
    () => readContactInquiryDraft(inquiryDraftOwnerId, id)?.message || "",
  )
  const [inquiryLoading, setInquiryLoading] = useState(false)
  const [inquiryKey, setInquiryKey] = useState(
    () => readContactInquiryDraft(inquiryDraftOwnerId, id)?.idempotencyKey || crypto.randomUUID(),
  )
  const [inquirySuccess, setInquirySuccess] = useState(null)

  const [isFavorite, setIsFavorite] = useState(false)
  const [favoriteLoading, setFavoriteLoading] = useState(false)
  const [favoriteStatus, setFavoriteStatus] = useState(
    () => localStorage.getItem("access_token") ? "loading" : "guest",
  )
  const [favoriteAttempt, setFavoriteAttempt] = useState(0)
  const [shareMessage, setShareMessage] = useState("")

  const [currentUserId, setCurrentUserId] = useState(null)
  const [identityStatus, setIdentityStatus] = useState(
    () => localStorage.getItem("access_token") ? "loading" : "guest",
  )
  const [identityAttempt, setIdentityAttempt] = useState(0)

  useEffect(() => {
    saveContactInquiryDraft(inquiryDraftOwnerId, id, {
      message: inquiryMessage,
      idempotencyKey: inquiryKey,
    })
  }, [id, inquiryDraftOwnerId, inquiryKey, inquiryMessage])

  const fetchCurrentUser = useCallback(async (signal) => {
    const token = localStorage.getItem("access_token")

    if (!token) {
      setCurrentUserId(null)
      setIdentityStatus("guest")
      return
    }

    setIdentityStatus("loading")

    try {
      const response = await apiFetch(
        "/users/me",
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          signal,
        }
      )

      if (!response.ok) {
        throw new Error("Unable to verify the signed-in account.")
      }

      const data = await readApiResponse(response)

      setCurrentUserId(data.id)
      setIdentityStatus("ready")
    } catch (error) {
      if (!signal.aborted) {
        console.error("Current user error:", error)
        setCurrentUserId(null)
        setIdentityStatus("error")
      }
    }
  }, [])

  const checkFavorite = useCallback(async (signal) => {
    const token = localStorage.getItem("access_token")

    if (!token) {
      setFavoriteStatus("guest")
      return
    }

    setFavoriteStatus("loading")

    try {
      const response = await apiFetch(
        `/favorites/${id}/status`,
        {
          headers: {
            Authorization: `Bearer ${token}`,
          },
          signal,
        }
      )

      if (!response.ok) {
        throw new Error("Unable to verify whether this listing is already saved.")
      }

      const data = await readApiResponse(response)

      setIsFavorite(data.is_favorite === true)
      setFavoriteStatus("ready")
    } catch (error) {
      if (!signal.aborted) {
        console.error("Favorite check error:", error)
        setFavoriteStatus("error")
      }
    }
  }, [id])

  const fetchProperty = useCallback(async (signal) => {
    setLoading(true)
    setError("")

    try {
      const response = await apiFetch(`/properties/${id}`, { signal })
      const data = await readApiResponse(response)

      if (!response.ok) {
        throw new Error(getApiError(data, "Property not found"))
      }

      setProperty(data)
      rememberRecentlyViewed(data)
      setActiveImageUrl(data.image_urls?.[0] || data.image_url || "")
      setTitle(data.title)
      setDescription(data.description || "")
      setImageUrl("")
      setImageUrls(data.image_urls || (data.image_url ? [data.image_url] : []))
      setPrice(data.price)
      setCurrency(data.currency || "USD")
      setListingType(data.listing_type || "sale")
      setAmenities(data.amenities || [])
      setLocation(data.location)
      setPropertyType(data.property_type)
      setBedrooms(data.bedrooms)
      setBathrooms(data.bathrooms)
      setSquareFeet(data.square_feet || "")
      setStatus(data.status)
    } catch (loadError) {
      if (!signal?.aborted) {
        console.error("Error fetching property:", loadError)
        setError(loadError.message)
      }
    } finally {
      if (!signal?.aborted) setLoading(false)
    }
  }, [id])

  useEffect(() => {
    const controller = new AbortController()
    const loadTimer = window.setTimeout(() => fetchProperty(controller.signal), 0)

    return () => {
      window.clearTimeout(loadTimer)
      controller.abort()
    }
  }, [fetchProperty, propertyLoadAttempt])

  useEffect(() => {
    const controller = new AbortController()
    const identityTimer = window.setTimeout(() => {
      fetchCurrentUser(controller.signal)
    }, 0)

    return () => {
      window.clearTimeout(identityTimer)
      controller.abort()
    }
  }, [fetchCurrentUser, identityAttempt])

  useEffect(() => {
    const controller = new AbortController()
    const favoriteTimer = window.setTimeout(() => checkFavorite(controller.signal), 0)

    return () => {
      window.clearTimeout(favoriteTimer)
      controller.abort()
    }
  }, [checkFavorite, favoriteAttempt])

  useEffect(() => {
    imagePreviewsRef.current = imagePreviews
  }, [imagePreviews])

  useEffect(() => {
    return () => {
      imagePreviewsRef.current.forEach((preview) => URL.revokeObjectURL(preview))
    }
  }, [])

  function resetEditFields() {
    if (!property) return
    setTitle(property.title)
    setDescription(property.description || "")
    setImageUrl("")
    setImageUrls(property.image_urls || (property.image_url ? [property.image_url] : []))
    setPrice(property.price)
    setCurrency(property.currency || "USD")
    setListingType(property.listing_type || "sale")
    setAmenities(property.amenities || [])
    setLocation(property.location)
    setPropertyType(property.property_type)
    setBedrooms(property.bedrooms)
    setBathrooms(property.bathrooms)
    setSquareFeet(property.square_feet || "")
    setStatus(property.status)
    clearSelectedImages()
    setError("")
  }

  function beginEditing() {
    resetEditFields()
    setEditing(true)
  }

  function cancelEditing() {
    resetEditFields()
    setEditing(false)
  }

  async function handleInquiry(event) {
    event.preventDefault()

    const token = localStorage.getItem("access_token")

    if (!token) {
      navigate("/login", { state: { returnTo: getReturnPath(routeLocation) } })
      return
    }

    if (!inquiryMessage.trim()) {
      setError("Please enter a message.")
      return
    }

    setInquiryLoading(true)
    setError("")

    try {
      const response = await apiFetch(
        `/inquiries/${id}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
            "Idempotency-Key": inquiryKey,
          },
          body: JSON.stringify({
            message: inquiryMessage,
          }),
        }
      )

      const data = await readApiResponse(response)

      if (!response.ok) {
        throw new Error(
          getApiError(data, "Failed to send inquiry")
        )
      }

      setInquirySuccess({ inquiryId: data.id, propertyId: data.property_id })
      clearContactInquiryDraft(inquiryDraftOwnerId, id)
      setInquiryMessage("")
      setInquiryKey(crypto.randomUUID())
      setShowInquiry(false)
    } catch (error) {
      console.error("Inquiry error:", error)
      setError(error.message)
    } finally {
      setInquiryLoading(false)
    }
  }

  function toggleInquiryForm() {
    if (!localStorage.getItem("access_token")) {
      navigate("/login", { state: { returnTo: getReturnPath(routeLocation) } })
      return
    }

    setInquirySuccess(null)
    setShowInquiry((current) => !current)
  }

  async function handleFavorite() {
    const token = localStorage.getItem("access_token")

    if (!token) {
      navigate("/login", { state: { returnTo: getReturnPath(routeLocation) } })
      return
    }

    setFavoriteLoading(true)
    setError("")

    try {
      const response = await apiFetch(
        `/favorites/${id}`,
        {
          method: isFavorite ? "DELETE" : "POST",
          headers: {
            Authorization: `Bearer ${token}`,
          },
        }
      )

      const data = await readApiResponse(response)

      if (!response.ok) {
        throw new Error(
          getApiError(data, "Failed to update favorite")
        )
      }

      setIsFavorite(!isFavorite)
      setFavoriteStatus("ready")
    } catch (error) {
      console.error("Favorite error:", error)
      setError(error.message)
    } finally {
      setFavoriteLoading(false)
    }
  }

  async function handleShare() {
    const result = await shareProperty(property, navigator, window.location.href)
    if (result.method === "clipboard") {
      setShareMessage("Property link copied.")
    } else if (result.method === "manual") {
      window.prompt("Copy this property link:", result.url)
      setShareMessage("Property link ready to copy.")
    } else if (result.method === "native") {
      setShareMessage("Property shared.")
    }
  }

  function showAdjacentImage(direction) {
    setActiveImageUrl((current) => getAdjacentImage(
      property.image_urls,
      current || property.image_url,
      direction,
    ))
  }

  function clearSelectedImages() {
    imagePreviews.forEach((preview) => URL.revokeObjectURL(preview))
    setImagePreviews([])
    setImageFiles([])
    setNewImagesAreCover(false)
  }

  function handleImageFiles(event) {
    const files = Array.from(event.target.files || [])
    setError("")
    if (!files.length) return

    if (imageUrls.length + files.length + (imageUrl ? 1 : 0) > 8) {
      setError("A property can have no more than 8 pictures.")
      event.target.value = ""
      return
    }
    if (files.some((file) => !["image/jpeg", "image/png", "image/webp"].includes(file.type))) {
      setError("Every picture must be a JPG, PNG, or WebP image.")
      event.target.value = ""
      return
    }
    if (files.some((file) => file.size > 5 * 1024 * 1024)) {
      setError("Each picture must be no larger than 5 MB.")
      event.target.value = ""
      return
    }

    clearSelectedImages()
    setImageFiles(files)
    setImagePreviews(files.map((file) => URL.createObjectURL(file)))
    setNewImagesAreCover(imageUrls.length === 0 && !imageUrl)
  }

  function removeExistingImage(index) {
    setImageUrls((current) => current.filter((_url, itemIndex) => itemIndex !== index))
  }

  function makeCoverImage(index) {
    setImageUrls((current) => [current[index], ...current.filter((_url, itemIndex) => itemIndex !== index)])
    setNewImagesAreCover(false)
  }

  function makeNewImageCover(index) {
    setImageFiles((current) => moveImageToCover(current, index))
    setImagePreviews((current) => moveImageToCover(current, index))
    setNewImagesAreCover(true)
  }

  function removeNewImage(index) {
    const preview = imagePreviews[index]
    if (preview) URL.revokeObjectURL(preview)
    const remainingCount = imageFiles.length - 1
    setImageFiles((current) => removeImageAt(current, index))
    setImagePreviews((current) => removeImageAt(current, index))
    if (newImagesAreCover && remainingCount <= 0) {
      setNewImagesAreCover(false)
    }
  }

  function fileToBase64(file) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = () => resolve(reader.result.split(",")[1])
      reader.onerror = () => reject(new Error("Could not read the selected image."))
      reader.readAsDataURL(file)
    })
  }

  async function uploadSingleImage(token, imageFile) {
    const response = await apiFetch("/uploads/property-images", {
      method: "POST",
      headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
      body: JSON.stringify({
        filename: imageFile.name,
        content_type: imageFile.type,
        data: await fileToBase64(imageFile),
      }),
    })
    const data = await readApiResponse(response)
    if (!response.ok) throw new Error(getApiError(data, "Failed to upload image"))
    return data.image_url
  }

  async function uploadImages(token) {
    const uploadedImageUrls = []
    try {
      for (const imageFile of imageFiles) {
        uploadedImageUrls.push(await uploadSingleImage(token, imageFile))
      }
      return uploadedImageUrls
    } catch (uploadError) {
      await Promise.all(uploadedImageUrls.map((url) => deleteUnusedUpload(token, url)))
      throw uploadError
    }
  }

  async function deleteUnusedUpload(token, uploadedImageUrl) {
    const imageName = uploadedImageUrl.split("/").pop()
    try {
      await apiFetch(`/uploads/property-images/${encodeURIComponent(imageName)}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` },
      })
    } catch (cleanupError) {
      console.error("Unused image cleanup failed:", cleanupError)
    }
  }

  async function handleUpdate(event) {
    event.preventDefault()

    const token = localStorage.getItem("access_token")

    if (!token) {
      setError("Please log in to update this property.")
      return
    }

    if (!imageUrls.length && !imageUrl.trim() && !imageFiles.length) {
      setError("Keep or add at least one property picture before saving.")
      return
    }

    setError("")
    setUpdateLoading(true)

    const hasNewUploads = imageFiles.length > 0
    try {
      const uploadedImageUrls = await uploadImages(token)
      const orderedImageUrls = newImagesAreCover
        ? [...uploadedImageUrls, ...imageUrls, ...(imageUrl ? [imageUrl] : [])]
        : [...imageUrls, ...(imageUrl ? [imageUrl] : []), ...uploadedImageUrls]
      const updatedImageUrls = Array.from(new Set(orderedImageUrls))
      if (updatedImageUrls.length > 8) {
        await Promise.all(uploadedImageUrls.map((url) => deleteUnusedUpload(token, url)))
        throw new Error("A property can have no more than 8 pictures.")
      }
      if (!updatedImageUrls.length) {
        throw new Error("Keep or add at least one property picture before saving.")
      }
      const response = await apiFetch(`/properties/${id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "X-Property-Version": String(property.version),
        },
        body: JSON.stringify({
          title,
          description,
          image_url: updatedImageUrls[0] || "",
          image_urls: updatedImageUrls,
          price: Number(price),
          currency,
          listing_type: listingType,
          amenities,
          location,
          property_type: propertyType,
          bedrooms: Number(bedrooms),
          bathrooms: Number(bathrooms),
          square_feet: squareFeet === "" ? 0 : Number(squareFeet),
          status,
        }),
      })
      const data = await readApiResponse(response)
      if (!response.ok) {
        if (hasNewUploads) {
          await Promise.all(uploadedImageUrls.map((url) => deleteUnusedUpload(token, url)))
        }
        throw new Error(getApiError(data, "Failed to update property"))
      }

      setProperty(data)
      setActiveImageUrl(data.image_urls?.[0] || data.image_url || "")
      setImageUrl("")
      setImageUrls(data.image_urls || (data.image_url ? [data.image_url] : []))
      clearSelectedImages()
      setEditing(false)
      alert("Property updated successfully!")
    } catch (updateError) {
      console.error("Update error:", updateError)
      setError(updateError.message)
    } finally {
      setUpdateLoading(false)
    }
  }

  async function handleDelete() {
    const token = localStorage.getItem("access_token")

    if (!token) {
      setError("Please log in to delete this property.")
      return
    }

    const confirmed = window.confirm(
      "Are you sure you want to delete this property?"
    )

    if (!confirmed) {
      return
    }

    if (deleteLoading) return
    setDeleteLoading(true)
    setError("")

    try {
      const response = await apiFetch(`/properties/${id}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
          "X-Property-Version": String(property.version),
        },
      })
      const data = await readApiResponse(response)

      if (!response.ok) {
        throw new Error(getApiError(data, "Failed to delete property"))
      }

      navigate("/my-properties", { replace: true })
    } catch (deleteError) {
      console.error("Delete error:", deleteError)
      setError(deleteError.message)
      setDeleteLoading(false)
    }
  }

  if (loading) {
    return <p>Loading property...</p>
  }

  if (error && !property) {
    return (
      <div className="property-load-failure" role="alert">
        <h1>Unable to load property</h1>
        <p>{error}</p>
        <button type="button" onClick={() => setPropertyLoadAttempt((current) => current + 1)}>
          Try again
        </button>
        <Link to="/">Back to properties</Link>
      </div>
    )
  }

  if (!property) {
    return <h1>Property not found</h1>
  }

  const isOwner =
    identityStatus === "ready" &&
    currentUserId !== null &&
    currentUserId === property.owner_id
  const canUseBuyerActions =
    identityStatus === "guest"
    || (identityStatus === "ready" && !isOwner)
  const isAvailable =
    property.status?.toLowerCase() === "available"

  return (
    <div className="property-details-page">

      <Link to="/" className="back-link">
        ← Back to properties
      </Link>

      {error && (
        <p className="property-error">
          {error}
        </p>
      )}

      {editing ? (

        <div className="property-edit-form">

          <h1>Edit Property</h1>

          <form onSubmit={handleUpdate}>

            <label>
              Title
              <input
                type="text"
                value={title}
                onChange={(event) =>
                  setTitle(event.target.value)
                }
                required
              />
            </label>

            <label>
              Description (optional)
              <textarea
                value={description}
                onChange={(event) =>
                  setDescription(event.target.value)
                }
                rows="5"
                maxLength="2000"
              />
            </label>

            <label className="property-edit-image-field">
              Property pictures
              {imageUrls.length > 0 && (
                <span className="property-edit-gallery">
                  {imageUrls.map((url, index) => (
                    <span className="property-edit-gallery-item" key={url}>
                      <img src={url} alt={`Property ${index + 1}`} />
                      <span>{index === 0 ? "Cover" : `Picture ${index + 1}`}</span>
                      {index > 0 && (
                        <button type="button" onClick={() => makeCoverImage(index)}>Make cover</button>
                      )}
                      <button type="button" onClick={() => removeExistingImage(index)}>Remove</button>
                    </span>
                  ))}
                </span>
              )}
              <span className="property-edit-upload-button">
                Add pictures
                <input type="file" multiple accept="image/jpeg,image/png,image/webp" onChange={handleImageFiles} />
              </span>
              <small>Required · keep or add at least one picture · up to 8 total · JPG, PNG, or WebP · 5 MB each</small>
              {imagePreviews.length > 0 && (
                <span className="property-edit-new-images">
                  {imagePreviews.map((preview, index) => (
                    <span className="property-edit-gallery-item" key={preview}>
                      <img src={preview} alt={`New property preview ${index + 1}`} />
                      <span>
                        {index === 0 && newImagesAreCover ? "New cover" : `New picture ${index + 1}`}
                      </span>
                      {!(index === 0 && newImagesAreCover) && (
                        <button type="button" onClick={() => makeNewImageCover(index)}>
                          Make cover
                        </button>
                      )}
                      <button type="button" onClick={() => removeNewImage(index)}>
                        Remove
                      </button>
                    </span>
                  ))}
                  <button type="button" onClick={clearSelectedImages}>Cancel new pictures</button>
                </span>
              )}
              <span className="property-edit-image-or">or add one image URL</span>
              <input
                type="url"
                value={imageUrl}
                onChange={(event) => {
                  setImageUrl(event.target.value)
                }}
                maxLength="2000"
                placeholder="https://example.com/property.jpg"
              />
            </label>

            <label>
              Listing For
              <select value={listingType} onChange={(event) => setListingType(event.target.value)}>
                <option value="sale">For Sale</option>
                <option value="rent">For Rent</option>
              </select>
            </label>

            <label>
              Currency
              <select value={currency} onChange={(event) => setCurrency(event.target.value)}>
                <option value="USD">US Dollars (US$)</option>
                <option value="DOP">Dominican Pesos (RD$)</option>
              </select>
            </label>

            <label>
              {listingType === "rent" ? "Monthly Rent" : "Sale Price"}
              <input
                type="number"
                value={price}
                onChange={(event) =>
                  setPrice(event.target.value)
                }
                required
              />
            </label>

            <label>
              Location
              <input
                type="text"
                list="dominican-location-suggestions"
                value={location}
                onChange={(event) =>
                  setLocation(event.target.value)
                }
                required
              />
              <span className="location-edit-help">
                Add sector, city/province, and country when possible. A private street address is not required.
              </span>
              <DominicanLocationSuggestions />
            </label>

            {location.trim() && (
              <div className="property-edit-location-preview">
                {!isMapLocationDetailed(location) && (
                  <span>Add a city/province or country to make this map search more reliable.</span>
                )}
                <a href={buildPropertyMapUrl(location)} target="_blank" rel="noreferrer">
                  Preview map search ↗
                </a>
              </div>
            )}

            <label>
              Property Type

              <select
                value={propertyType}
                onChange={(event) =>
                  setPropertyType(event.target.value)
                }
                required
              >
                <option value="House">House</option>
                <option value="Villa">Villa</option>
                <option value="Apartment">Apartment</option>
                <option value="Condo">Condo</option>
              </select>
            </label>

            <label>
              Bedrooms

              <input
                type="number"
                value={bedrooms}
                onChange={(event) =>
                  setBedrooms(event.target.value)
                }
                required
              />
            </label>

            <label>
              Bathrooms

              <input
                type="number"
                min="0"
                max="100"
                value={bathrooms}
                onChange={(event) =>
                  setBathrooms(event.target.value)
                }
                required
              />
            </label>

            <label>
              Square Feet (optional)

              <input
                type="number"
                min="0"
                max="10000000"
                value={squareFeet}
                onChange={(event) =>
                  setSquareFeet(event.target.value)
                }
                placeholder="1800"
              />
            </label>

            <label>
              Status

              <select
                value={status}
                onChange={(event) =>
                  setStatus(event.target.value)
                }
              >
                <option value="available">
                  Available
                </option>

                <option value="unavailable">
                  Unavailable
                </option>
              </select>
            </label>

            <fieldset className="property-edit-amenities">
              <legend>Amenities (optional)</legend>
              <div className="property-edit-amenities-options">
                {PROPERTY_AMENITIES.map((amenity) => (
                  <label key={amenity}>
                    <input
                      type="checkbox"
                      checked={amenities.includes(amenity)}
                      onChange={() => setAmenities((current) => current.includes(amenity) ? current.filter((item) => item !== amenity) : [...current, amenity])}
                    />
                    {amenity}
                  </label>
                ))}
              </div>
            </fieldset>

            <div>

              <button type="submit" disabled={updateLoading}>
                {updateLoading ? "Saving..." : "Save Changes"}
              </button>

              <button
                type="button"
                disabled={updateLoading}
                onClick={() => {
                  cancelEditing()
                }}
              >
                Cancel
              </button>

            </div>

          </form>
        </div>

      ) : (

        <div className="property-details">

          <div className="property-gallery">
            <div className="property-details-image">
              <PropertyImage
                imageUrl={activeImageUrl || property.image_url}
                title={property.title}
                priority
              />
              {property.image_urls?.length > 1 && (
                <>
                  <button
                    type="button"
                    className="property-gallery-arrow property-gallery-arrow-previous"
                    onClick={() => showAdjacentImage(-1)}
                    aria-label="Show previous property picture"
                  >
                    ‹
                  </button>
                  <button
                    type="button"
                    className="property-gallery-arrow property-gallery-arrow-next"
                    onClick={() => showAdjacentImage(1)}
                    aria-label="Show next property picture"
                  >
                    ›
                  </button>
                </>
              )}
            </div>
            {property.image_urls?.length > 1 && (
              <div className="property-gallery-thumbnails" aria-label="Property pictures">
                {property.image_urls.map((url, index) => (
                  <button
                    type="button"
                    key={url}
                    className={url === activeImageUrl ? "active" : ""}
                    onClick={() => setActiveImageUrl(url)}
                    aria-label={`View property picture ${index + 1}`}
                  >
                    <PropertyImage imageUrl={url} title={property.title} position={index + 1} />
                  </button>
                ))}
              </div>
            )}
          </div>

          <div className="property-details-content">

            <h1>{property.title}</h1>

            <p className="property-reference">Listing {formatPropertyReference(property.id)}</p>

            <p className="property-location">
              📍 {property.location}
            </p>

            <a
              className="property-map-link"
              href={buildPropertyMapUrl(property.location)}
              target="_blank"
              rel="noreferrer"
            >
              Open location in maps ↗
            </a>

            <p className="property-map-note">
              Approximate area based on the seller's description. Confirm the exact location with the seller.
            </p>

            <p className="property-owner">
              Listed by {property.owner_name}
            </p>

            {getListingFreshness(property.created_at, property.updated_at) && (
              <p className="property-listed-date">
                {getListingFreshness(property.created_at, property.updated_at)}
              </p>
            )}

            {property.description && (
              <p className="property-description">
                {property.description}
              </p>
            )}

            {property.amenities?.length > 0 && (
              <div className="property-amenities">
                {property.amenities.map((amenity) => <span key={amenity}>{amenity}</span>)}
              </div>
            )}

            <p className="property-price">
              {formatPropertyPrice(property.price, property.currency, property.listing_type)}
            </p>

            <p className="property-listing-label">
              {property.listing_type === "rent" ? "For Rent" : "For Sale"}
            </p>

            <div className="property-info">

              <div>
                <span>🛏</span>
                <strong>{property.bedrooms}</strong>
                <p>Bedrooms</p>
              </div>

              <div>
                <span>🛁</span>
                <strong>{property.bathrooms}</strong>
                <p>Bathrooms</p>
              </div>

              {property.square_feet > 0 && (
                <div>
                  <span>📐</span>
                  <strong>
                    {Number(property.square_feet).toLocaleString()}
                  </strong>
                  <p>Square Feet</p>
                </div>
              )}

              <div>
                <span>🏠</span>
                <strong>{property.property_type}</strong>
                <p>Property Type</p>
              </div>

              <div>
                <span>●</span>
                <strong>
                  {["available", "open"].includes(
                    property.status?.toLowerCase()
                  )
                    ? "Available"
                    : "Unavailable"}
                </strong>
                <p>Status</p>
              </div>

            </div>

            <div className="property-actions">

              <button
                type="button"
                className="share-button"
                onClick={handleShare}
              >
                Share
              </button>

              {canUseBuyerActions && isAvailable && (
                <>
                  <button
                    onClick={toggleInquiryForm}
                  >
                    {showInquiry
                      ? "Close"
                      : "Contact Owner"}
                  </button>

                  {(favoriteStatus === "guest" || favoriteStatus === "ready") && (
                    <button
                      className="favorite-button"
                      onClick={handleFavorite}
                      disabled={favoriteLoading}
                    >
                      {favoriteLoading
                        ? "Saving..."
                        : isFavorite
                          ? "❤️ Favorited"
                          : "♡ Favorite"}
                    </button>
                  )}
                  {favoriteStatus === "loading" && (
                    <span className="favorite-state" role="status">Checking saved status…</span>
                  )}
                  {favoriteStatus === "error" && (
                    <span className="favorite-state favorite-state-error" role="alert">
                      Saved status unavailable.
                      <button type="button" onClick={() => setFavoriteAttempt((current) => current + 1)}>
                        Retry
                      </button>
                    </span>
                  )}
                </>
              )}

              {!isOwner && !isAvailable && (
                <p className="property-unavailable-message">
                  This property is not accepting new inquiries.
                </p>
              )}

              {isOwner && (
                <>
                  <button
                    onClick={() =>
                      beginEditing()
                    }
                  >
                    Edit Property
                  </button>

                  <button onClick={handleDelete} disabled={deleteLoading || updateLoading}>
                    {deleteLoading ? "Deleting..." : "Delete Property"}
                  </button>
                </>
              )}

              {identityStatus === "loading" && (
                <span className="identity-status" role="status">Checking account access…</span>
              )}

              {identityStatus === "error" && (
                <span className="identity-status identity-error" role="alert">
                  Account access could not be verified.
                  <button type="button" onClick={() => setIdentityAttempt((current) => current + 1)}>
                    Try again
                  </button>
                </span>
              )}

            </div>

            <p className="share-message" aria-live="polite">{shareMessage}</p>

            {inquirySuccess && (
              <div className="inquiry-success" role="status">
                <div>
                  <strong>Inquiry sent successfully.</strong>
                  <span>You can continue messaging the owner from your inquiries.</span>
                </div>
                <Link to={`/inquiries?property=${formatPropertyReference(inquirySuccess.propertyId)}`}>
                  Open conversation
                </Link>
              </div>
            )}

            {showInquiry && canUseBuyerActions && isAvailable && (
              <div className="inquiry-form">

                <div className="inquiry-form-heading">
                  <div>
                    <h2>Contact owner</h2>
                    <p>Ask about availability, a viewing, or any property details.</p>
                  </div>
                  <span>Reference {formatPropertyReference(property.id)}</span>
                </div>

                <form onSubmit={handleInquiry}>

                  <label htmlFor="owner-message">Your message</label>

                  <div className="inquiry-quick-prompts" aria-label="Suggested messages">
                    {INQUIRY_PROMPTS.map((prompt) => (
                      <button
                        type="button"
                        key={prompt}
                        onClick={() => setInquiryMessage((current) => {
                          if (current.includes(prompt)) return current
                          return `${current.trim()}${current.trim() ? "\n" : ""}${prompt}`.slice(0, 1000)
                        })}
                      >
                        {prompt}
                      </button>
                    ))}
                  </div>

                  <textarea
                    id="owner-message"
                    value={inquiryMessage}
                    onChange={(event) =>
                      setInquiryMessage(
                        event.target.value
                      )
                    }
                    placeholder="Write a message to the owner..."
                    rows="5"
                    maxLength="1000"
                    disabled={inquiryLoading}
                    onKeyDown={(event) => {
                      if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
                        event.currentTarget.form?.requestSubmit()
                      }
                    }}
                    required
                  />

                  <div className="inquiry-form-footer">

                    <span>Session draft saved · {inquiryMessage.length}/1000 · Ctrl/⌘ + Enter to send</span>

                    <div className="inquiry-form-actions">

                    <button
                      type="submit"
                      disabled={inquiryLoading || !inquiryMessage.trim()}
                    >
                      {inquiryLoading
                        ? "Sending..."
                        : "Send Inquiry"}
                    </button>

                    <button
                      type="button"
                      disabled={!inquiryMessage || inquiryLoading}
                      onClick={() => {
                        clearContactInquiryDraft(inquiryDraftOwnerId, id)
                        setInquiryMessage("")
                        setInquiryKey(crypto.randomUUID())
                      }}
                    >
                      Clear
                    </button>

                    <button
                      type="button"
                      onClick={() =>
                        setShowInquiry(false)
                      }
                    >
                      Cancel
                    </button>

                    </div>

                  </div>

                </form>

              </div>
            )}

          </div>
        </div>
      )}
    </div>
  )
}

export default PropertyDetails
