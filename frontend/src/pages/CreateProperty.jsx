import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { getApiError } from "../utils/apiError"
import { PROPERTY_AMENITIES } from "../utils/propertyOptions"
import { readApiResponse } from "../utils/apiResponse"
import "./CreateProperty.css"
import { apiFetch } from "../utils/apiFetch"
import {
  clearListingDraft,
  createListingKey,
  getDraftOwnerId,
  hasListingDraft,
  readListingDraft,
  saveListingDraft,
} from "../utils/listingDraft"
import { moveImageToCover, removeImageAt } from "../utils/imageOrder"
import DominicanLocationSuggestions from "../components/DominicanLocationSuggestions"
import { buildPropertyMapUrl, isMapLocationDetailed } from "../utils/propertyMap"

function CreateProperty() {
  const navigate = useNavigate()
  const draftOwnerId = getDraftOwnerId(localStorage.getItem("access_token"))
  const initialDraft = readListingDraft(draftOwnerId)
  const [idempotencyKey, setIdempotencyKey] = useState(
    initialDraft?.idempotencyKey || createListingKey()
  )
  const [title, setTitle] = useState(initialDraft?.title || "")
  const [description, setDescription] = useState(initialDraft?.description || "")
  const [imageUrl, setImageUrl] = useState(initialDraft?.imageUrl || "")
  const [imageFiles, setImageFiles] = useState([])
  const [imagePreviews, setImagePreviews] = useState([])
  const imagePreviewsRef = useRef([])
  const [price, setPrice] = useState(initialDraft?.price || "")
  const [currency, setCurrency] = useState(initialDraft?.currency || "USD")
  const [listingType, setListingType] = useState(initialDraft?.listingType || "sale")
  const [amenities, setAmenities] = useState(initialDraft?.amenities || [])
  const [location, setLocation] = useState(initialDraft?.location || "")
  const [propertyType, setPropertyType] = useState(initialDraft?.propertyType || "")
  const [bedrooms, setBedrooms] = useState(initialDraft?.bedrooms || "")
  const [bathrooms, setBathrooms] = useState(initialDraft?.bathrooms || "1")
  const [squareFeet, setSquareFeet] = useState(initialDraft?.squareFeet || "")
  const [status, setStatus] = useState(initialDraft?.status || "available")
  const [draftRestored, setDraftRestored] = useState(hasListingDraft(initialDraft))
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    imagePreviewsRef.current = imagePreviews
  }, [imagePreviews])

  useEffect(() => {
    return () => {
      imagePreviewsRef.current.forEach((preview) => URL.revokeObjectURL(preview))
    }
  }, [])

  useEffect(() => {
    const timer = window.setTimeout(() => {
      saveListingDraft(draftOwnerId, {
        title, description, imageUrl, price, currency, listingType, amenities, location,
        propertyType, bedrooms, bathrooms, squareFeet, status,
        idempotencyKey,
      })
    }, 400)
    return () => window.clearTimeout(timer)
  }, [
    amenities, bathrooms, bedrooms, currency, description, draftOwnerId, imageUrl,
    idempotencyKey, listingType, location, price, propertyType, squareFeet, status, title,
  ])

  function discardDraft() {
    if (!window.confirm("Discard this unfinished property listing?")) return
    clearListingDraft(draftOwnerId)
    setTitle("")
    setDescription("")
    setImageUrl("")
    setPrice("")
    setCurrency("USD")
    setListingType("sale")
    setAmenities([])
    setLocation("")
    setPropertyType("")
    setBedrooms("")
    setBathrooms("1")
    setSquareFeet("")
    setStatus("available")
    setIdempotencyKey(createListingKey())
    setDraftRestored(false)
    clearSelectedImages()
  }

  function clearSelectedImages() {
    imagePreviews.forEach((preview) => URL.revokeObjectURL(preview))
    setImagePreviews([])
    setImageFiles([])
  }

  function handleImageFiles(event) {
    const files = Array.from(event.target.files || [])
    setError("")
    if (!files.length) return

    if (files.length > 8) {
      setError("Choose no more than 8 pictures.")
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
    setImageUrl("")
    setImagePreviews(files.map((file) => URL.createObjectURL(file)))
  }

  function makeSelectedImageCover(index) {
    setImageFiles((current) => moveImageToCover(current, index))
    setImagePreviews((current) => moveImageToCover(current, index))
  }

  function removeSelectedImage(index) {
    const preview = imagePreviews[index]
    if (preview) URL.revokeObjectURL(preview)
    setImageFiles((current) => removeImageAt(current, index))
    setImagePreviews((current) => removeImageAt(current, index))
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
    if (!imageFiles.length) return imageUrl ? [imageUrl] : []
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

  async function handleSubmit(event) {
    event.preventDefault()
    const token = localStorage.getItem("access_token")
    if (!token) {
      setError("You must be logged in to create a property.")
      return
    }

    if (!imageFiles.length && !imageUrl.trim()) {
      setError("Add at least one property picture before publishing.")
      return
    }

    setError("")
    setLoading(true)
    const hasNewUploads = imageFiles.length > 0
    try {
      const uploadedImageUrls = await uploadImages(token)
      const response = await apiFetch("/properties/", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          "Idempotency-Key": idempotencyKey,
        },
        body: JSON.stringify({
          title,
          description,
          image_url: uploadedImageUrls[0] || "",
          image_urls: uploadedImageUrls,
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
        throw new Error(getApiError(data, "Failed to create property"))
      }
      if (hasNewUploads) {
        const usedImages = new Set(data.image_urls || [])
        await Promise.all(
          uploadedImageUrls
            .filter((url) => !usedImages.has(url))
            .map((url) => deleteUnusedUpload(token, url))
        )
      }
      clearListingDraft(draftOwnerId)
      alert("Property created successfully!")
      navigate(`/properties/${data.id}`)
    } catch (submitError) {
      console.error("Error creating property:", submitError)
      setError(submitError.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="create-property-page">
      <div className="create-property-container">
        <h1>Create Property</h1>
        <p>List your property on the marketplace.</p>
        {draftRestored && (
          <div className="draft-restored" role="status">
            <div>
              <strong>Draft restored</strong>
              <p>Your saved details are back. Please reselect any picture files.</p>
            </div>
            <button type="button" onClick={discardDraft}>Discard draft</button>
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Title</label>
            <input type="text" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Beautiful family home" required />
          </div>
          <div className="form-group">
            <label>Description (optional)</label>
            <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Describe the property, neighborhood, and important features" rows="5" maxLength="2000" />
          </div>
          <div className="form-group">
            <label>Property pictures</label>
            <label className="image-upload-button">
              Choose pictures
              <input type="file" multiple accept="image/jpeg,image/png,image/webp" onChange={handleImageFiles} />
            </label>
            <span className="image-upload-help">Required · up to 8 JPG, PNG, or WebP pictures · 5 MB each · first picture is the cover</span>
            {imagePreviews.length > 0 && (
              <div className="image-preview-list">
                {imagePreviews.map((preview, index) => (
                  <span className="image-preview-item" key={preview}>
                    <img src={preview} alt={`Selected property preview ${index + 1}`} />
                    <span>{index === 0 ? "Cover" : `Picture ${index + 1}`}</span>
                    {index > 0 && (
                      <button type="button" onClick={() => makeSelectedImageCover(index)}>
                        Make cover
                      </button>
                    )}
                    <button type="button" onClick={() => removeSelectedImage(index)}>
                      Remove
                    </button>
                  </span>
                ))}
                <button type="button" className="remove-image-button" onClick={clearSelectedImages}>Remove pictures</button>
              </div>
            )}
            <span className="image-or">or paste an image URL</span>
            <input
              type="url"
              value={imageUrl}
              onChange={(event) => {
                setImageUrl(event.target.value)
                if (event.target.value) clearSelectedImages()
              }}
              placeholder="https://example.com/property.jpg"
              maxLength="2000"
            />
          </div>
          <div className="form-group">
            <label>Listing For</label>
            <select value={listingType} onChange={(event) => setListingType(event.target.value)}>
              <option value="sale">For Sale</option><option value="rent">For Rent</option>
            </select>
          </div>
          <div className="form-group">
            <label>Currency</label>
            <select value={currency} onChange={(event) => setCurrency(event.target.value)}>
              <option value="USD">US Dollars (US$)</option>
              <option value="DOP">Dominican Pesos (RD$)</option>
            </select>
          </div>
          <div className="form-group"><label>{listingType === "rent" ? "Monthly Rent" : "Sale Price"}</label><input type="number" value={price} onChange={(event) => setPrice(event.target.value)} placeholder={listingType === "rent" ? "2200" : "350000"} required /></div>
          <div className="form-group">
            <label>Location</label>
            <input type="text" list="dominican-location-suggestions" value={location} onChange={(event) => setLocation(event.target.value)} placeholder="Sector, city/province, country" required />
            <p className="location-help">Add enough area detail for a useful map search. A private street address is not required.</p>
            {location.trim() && (
              <div className="location-map-preview">
                {!isMapLocationDetailed(location) && (
                  <span>Add a city/province or country to make this map search more reliable.</span>
                )}
                <a href={buildPropertyMapUrl(location)} target="_blank" rel="noreferrer">
                  Preview map search ↗
                </a>
              </div>
            )}
            <DominicanLocationSuggestions />
          </div>
          <div className="form-group">
            <label>Property Type</label>
            <select value={propertyType} onChange={(event) => setPropertyType(event.target.value)} required>
              <option value="">Select type</option><option value="House">House</option><option value="Villa">Villa</option><option value="Apartment">Apartment</option><option value="Condo">Condo</option>
            </select>
          </div>
          <div className="form-group"><label>Bedrooms</label><input type="number" min="1" value={bedrooms} onChange={(event) => setBedrooms(event.target.value)} required /></div>
          <div className="form-group"><label>Bathrooms</label><input type="number" min="0" max="100" value={bathrooms} onChange={(event) => setBathrooms(event.target.value)} required /></div>
          <div className="form-group"><label>Square Feet (optional)</label><input type="number" min="0" max="10000000" value={squareFeet} onChange={(event) => setSquareFeet(event.target.value)} placeholder="1800" /></div>
          <fieldset className="amenities-fieldset">
            <legend>Amenities (optional)</legend>
            <div className="amenities-options">
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
          <div className="form-group">
            <label>Status</label>
            <select value={status} onChange={(event) => setStatus(event.target.value)}><option value="available">Available</option><option value="unavailable">Unavailable</option></select>
          </div>
          {error && <p className="form-error">{error}</p>}
          <button type="submit" disabled={loading}>{loading ? "Creating..." : "Create Property"}</button>
        </form>
      </div>
    </div>
  )
}

export default CreateProperty
