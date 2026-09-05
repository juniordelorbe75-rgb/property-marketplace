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

const REPORT_REASONS = [
  ["suspected_scam", "Posible estafa o fraude"],
  ["misleading_information", "Información engañosa o incorrecta"],
  ["duplicate_listing", "Anuncio duplicado"],
  ["already_unavailable", "La propiedad ya no está disponible"],
  ["inappropriate_content", "Contenido inapropiado"],
  ["other", "Otra preocupación de seguridad"],
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

  const [showReport, setShowReport] = useState(false)
  const [reportReason, setReportReason] = useState("")
  const [reportDetails, setReportDetails] = useState("")
  const [reportLoading, setReportLoading] = useState(false)
  const [reportKey, setReportKey] = useState(() => crypto.randomUUID())
  const [reportSuccess, setReportSuccess] = useState(null)

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
        throw new Error("No pudimos verificar la cuenta que inició sesión.")
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
        throw new Error("No pudimos verificar si esta propiedad ya está guardada.")
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
        throw new Error(getApiError(data, "Propiedad no encontrada"))
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
      setError("Escriba un mensaje.")
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
          getApiError(data, "No pudimos enviar la consulta")
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
    setShowReport(false)
    setShowInquiry((current) => !current)
  }

  function toggleReportForm() {
    if (!localStorage.getItem("access_token")) {
      navigate("/login", { state: { returnTo: getReturnPath(routeLocation) } })
      return
    }

    setShowInquiry(false)
    setReportSuccess(null)
    setShowReport((current) => !current)
  }

  async function handleReport(event) {
    event.preventDefault()
    const token = localStorage.getItem("access_token")

    if (!token) {
      navigate("/login", { state: { returnTo: getReturnPath(routeLocation) } })
      return
    }
    if (!reportReason) {
      setError("Seleccione el motivo por el que debe revisarse este anuncio.")
      return
    }

    setReportLoading(true)
    setError("")

    try {
      const response = await apiFetch(
        `/reports/properties/${id}`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Authorization: `Bearer ${token}`,
            "Idempotency-Key": reportKey,
          },
          body: JSON.stringify({
            reason: reportReason,
            details: reportDetails,
          }),
        }
      )
      const data = await readApiResponse(response)

      if (!response.ok) {
        throw new Error(getApiError(data, "No pudimos enviar el reporte"))
      }

      setReportSuccess(data.id)
      setReportReason("")
      setReportDetails("")
      setReportKey(crypto.randomUUID())
      setShowReport(false)
    } catch (reportError) {
      console.error("Listing report error:", reportError)
      setError(reportError.message)
    } finally {
      setReportLoading(false)
    }
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
          getApiError(data, "No pudimos actualizar el favorito")
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
      setShareMessage("Enlace de la propiedad copiado.")
    } else if (result.method === "manual") {
      window.prompt("Copie este enlace de la propiedad:", result.url)
      setShareMessage("El enlace de la propiedad está listo para copiarse.")
    } else if (result.method === "native") {
      setShareMessage("Propiedad compartida.")
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
      reader.onerror = () => reject(new Error("No pudimos leer la imagen seleccionada."))
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
    if (!response.ok) throw new Error(getApiError(data, "No pudimos cargar la imagen"))
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
      setError("Inicie sesión para actualizar esta propiedad.")
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
          country_code: property.country_code || "DO",
          province: property.province || "",
          municipality: property.municipality || "",
          sector: property.sector || "",
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
        throw new Error(getApiError(data, "No pudimos actualizar la propiedad"))
      }

      setProperty(data)
      setActiveImageUrl(data.image_urls?.[0] || data.image_url || "")
      setImageUrl("")
      setImageUrls(data.image_urls || (data.image_url ? [data.image_url] : []))
      clearSelectedImages()
      setEditing(false)
      alert("¡Propiedad actualizada correctamente!")
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
      setError("Inicie sesión para eliminar esta propiedad.")
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
        throw new Error(getApiError(data, "No pudimos eliminar la propiedad"))
      }

      navigate("/my-properties", { replace: true })
    } catch (deleteError) {
      console.error("Delete error:", deleteError)
      setError(deleteError.message)
      setDeleteLoading(false)
    }
  }

  if (loading) {
    return <p>Cargando propiedad...</p>
  }

  if (error && !property) {
    return (
      <div className="property-load-failure" role="alert">
        <h1>No pudimos cargar la propiedad</h1>
        <p>{error}</p>
        <button type="button" onClick={() => setPropertyLoadAttempt((current) => current + 1)}>
          Try again
        </button>
        <Link to="/">Volver a las propiedades</Link>
      </div>
    )
  }

  if (!property) {
    return <h1>Propiedad no encontrada</h1>
  }

  const isOwner =
    identityStatus === "ready" &&
    currentUserId !== null &&
    currentUserId === property.owner_id
  const canUseBuyerActions =
    identityStatus === "guest"
    || (identityStatus === "ready" && !isOwner)
  const isAvailable =
    property.status?.toLowerCase() === "available" && !property.safety_hold

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

          <h1>Editar propiedad</h1>

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
                      <span>{index === 0 ? "Portada" : `Imagen ${index + 1}`}</span>
                      {index > 0 && (
                        <button type="button" onClick={() => makeCoverImage(index)}>Usar como portada</button>
                      )}
                      <button type="button" onClick={() => removeExistingImage(index)}>Eliminar</button>
                    </span>
                  ))}
                </span>
              )}
              <span className="property-edit-upload-button">
                Add pictures
                <input type="file" multiple accept="image/jpeg,image/png,image/webp" onChange={handleImageFiles} />
              </span>
              <small>Obligatorio · conserve o agregue al menos una imagen · máximo 8 · JPG, PNG o WebP · 5 MB cada una</small>
              {imagePreviews.length > 0 && (
                <span className="property-edit-new-images">
                  {imagePreviews.map((preview, index) => (
                    <span className="property-edit-gallery-item" key={preview}>
                      <img src={preview} alt={`New property preview ${index + 1}`} />
                      <span>
                        {index === 0 && newImagesAreCover ? "Nueva portada" : `Nueva imagen ${index + 1}`}
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
                  <button type="button" onClick={clearSelectedImages}>Cancelar imágenes nuevas</button>
                </span>
              )}
              <span className="property-edit-image-or">o agregue la dirección de una imagen</span>
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
                <option value="sale">En venta</option>
                <option value="rent">En alquiler</option>
              </select>
            </label>

            <label>
              Currency
              <select value={currency} onChange={(event) => setCurrency(event.target.value)}>
                <option value="USD">Dólares estadounidenses (US$)</option>
                <option value="DOP">Pesos dominicanos (RD$)</option>
              </select>
            </label>

            <label>
              {listingType === "rent" ? "Alquiler mensual" : "Precio de venta"}
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
                  <span>Agregue una ciudad, provincia o país para mejorar la búsqueda en el mapa.</span>
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
                <option value="House">Casa</option>
                <option value="Villa">Villa</option>
                <option value="Apartment">Apartamento</option>
                <option value="Condo">Condominio</option>
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
                <option value="available" disabled={property.safety_hold}>
                  Available
                </option>

                <option value="unavailable">
                  No disponible
                </option>
              </select>
            </label>

            <fieldset className="property-edit-amenities">
              <legend>Amenidades (opcional)</legend>
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
                {updateLoading ? "Guardando..." : "Guardar cambios"}
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
                    aria-label="Mostrar imagen anterior de la propiedad"
                  >
                    ‹
                  </button>
                  <button
                    type="button"
                    className="property-gallery-arrow property-gallery-arrow-next"
                    onClick={() => showAdjacentImage(1)}
                    aria-label="Mostrar imagen siguiente de la propiedad"
                  >
                    ›
                  </button>
                </>
              )}
            </div>
            {property.image_urls?.length > 1 && (
              <div className="property-gallery-thumbnails" aria-label="Imágenes de la propiedad">
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

            {property.safety_hold && (
              <div className="property-safety-hold" role="status">
                <strong>Este anuncio no está disponible temporalmente mientras se revisa su seguridad.</strong>
                <span>Está oculto de las búsquedas y las consultas nuevas están pausadas. El propietario todavía puede corregir sus detalles.</span>
              </div>
            )}

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
              {property.owner_profile_public && (
                <> · <Link to={`/profiles/${property.owner_id}`}>Ver perfil</Link></>
              )}
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
              {property.listing_type === "rent" ? "En alquiler" : "En venta"}
            </p>

            <div className="property-info">

              <div>
                <span>🛏</span>
                <strong>{property.bedrooms}</strong>
                <p>Habitaciones</p>
              </div>

              <div>
                <span>🛁</span>
                <strong>{property.bathrooms}</strong>
                <p>Baños</p>
              </div>

              {property.square_feet > 0 && (
                <div>
                  <span>📐</span>
                  <strong>
                    {Number(property.square_feet).toLocaleString()}
                  </strong>
                  <p>Pies cuadrados</p>
                </div>
              )}

              <div>
                <span>🏠</span>
                <strong>{property.property_type}</strong>
                <p>Tipo de propiedad</p>
              </div>

              <div>
                <span>●</span>
                <strong>
                  {property.safety_hold
                    ? "En revisión"
                    : ["available", "open"].includes(property.status?.toLowerCase())
                    ? "Disponible"
                    : "No disponible"}
                </strong>
                <p>Estado</p>
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

              {canUseBuyerActions && (
                <button
                  type="button"
                  className="report-button"
                  onClick={toggleReportForm}
                  disabled={reportLoading}
                >
                  {showReport ? "Cerrar reporte" : "Reportar anuncio"}
                </button>
              )}

              {canUseBuyerActions && isAvailable && (
                <>
                  <button
                    onClick={toggleInquiryForm}
                  >
                    {showInquiry
                      ? "Cerrar"
                      : "Contactar al propietario"}
                  </button>

                  {(favoriteStatus === "guest" || favoriteStatus === "ready") && (
                    <button
                      className="favorite-button"
                      onClick={handleFavorite}
                      disabled={favoriteLoading}
                    >
                      {favoriteLoading
                        ? "Guardando..."
                        : isFavorite
                          ? "❤️ Favorited"
                          : "♡ Favorite"}
                    </button>
                  )}
                  {favoriteStatus === "loading" && (
                    <span className="favorite-state" role="status">Comprobando favorito…</span>
                  )}
                  {favoriteStatus === "error" && (
                    <span className="favorite-state favorite-state-error" role="alert">
                      El estado del favorito no está disponible.
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
                    Editar propiedad
                  </button>

                  <button onClick={handleDelete} disabled={deleteLoading || updateLoading}>
                    {deleteLoading ? "Eliminando..." : "Eliminar propiedad"}
                  </button>
                </>
              )}

              {identityStatus === "loading" && (
                <span className="identity-status" role="status">Comprobando acceso a la cuenta…</span>
              )}

              {identityStatus === "error" && (
                <span className="identity-status identity-error" role="alert">
                  No pudimos verificar el acceso a la cuenta.
                  <button type="button" onClick={() => setIdentityAttempt((current) => current + 1)}>
                    Try again
                  </button>
                </span>
              )}

            </div>

            <p className="share-message" aria-live="polite">{shareMessage}</p>

            {reportSuccess && (
              <div className="report-success" role="status">
                <div>
                  <strong>Reporte registrado.</strong>
                  <span>Safety report #{reportSuccess} was saved. You do not need to submit it again.</span>
                </div>
                <Link to="/my-reports">Ver mis reportes</Link>
              </div>
            )}

            {showReport && canUseBuyerActions && (
              <div className="report-form">
                <div className="report-form-heading">
                  <div>
                    <h2>Reportar este anuncio</h2>
                    <p>Utilice esta opción para informar problemas de seguridad, exactitud, duplicidad o disponibilidad.</p>
                  </div>
                  <span>Reference {formatPropertyReference(property.id)}</span>
                </div>

                <form onSubmit={handleReport}>
                  <label htmlFor="report-reason">Motivo</label>
                  <select
                    id="report-reason"
                    value={reportReason}
                    onChange={(event) => setReportReason(event.target.value)}
                    disabled={reportLoading}
                    required
                  >
                    <option value="">Seleccione un motivo</option>
                    {REPORT_REASONS.map(([value, label]) => (
                      <option key={value} value={value}>{label}</option>
                    ))}
                  </select>

                  <label htmlFor="report-details">Detalles adicionales (opcional)</label>
                  <textarea
                    id="report-details"
                    value={reportDetails}
                    onChange={(event) => setReportDetails(event.target.value)}
                    placeholder="Describa su inquietud. No incluya contraseñas ni información de pago."
                    rows="4"
                    maxLength="1000"
                    disabled={reportLoading}
                  />

                  <div className="report-form-footer">
                    <span>{reportDetails.length}/1000</span>
                    <div>
                      <button type="submit" disabled={reportLoading || !reportReason}>
                        {reportLoading ? "Enviando..." : "Enviar reporte"}
                      </button>
                      <button
                        type="button"
                        disabled={reportLoading}
                        onClick={() => setShowReport(false)}
                      >
                        Cancel
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            )}

            {inquirySuccess && (
              <div className="inquiry-success" role="status">
                <div>
                  <strong>Consulta enviada correctamente.</strong>
                  <span>Puede continuar la conversación con el propietario desde sus consultas.</span>
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
                    <h2>Contactar al propietario</h2>
                    <p>Pregunte sobre disponibilidad, visitas o cualquier detalle de la propiedad.</p>
                  </div>
                  <span>Reference {formatPropertyReference(property.id)}</span>
                </div>

                <form onSubmit={handleInquiry}>

                  <label htmlFor="owner-message">Su mensaje</label>

                  <div className="inquiry-quick-prompts" aria-label="Mensajes sugeridos">
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
                        ? "Enviando..."
                        : "Enviar consulta"}
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
