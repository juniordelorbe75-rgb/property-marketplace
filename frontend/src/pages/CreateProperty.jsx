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
import { buildPropertyMapUrl, isMapLocationDetailed } from "../utils/propertyMap"
import { buildDominicanLocation, DOMINICAN_PROVINCES } from "../utils/dominicanLocations"

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
  const [province, setProvince] = useState(initialDraft?.province || "")
  const [municipality, setMunicipality] = useState(initialDraft?.municipality || "")
  const [sector, setSector] = useState(initialDraft?.sector || "")
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
        province, municipality, sector,
        propertyType, bedrooms, bathrooms, squareFeet, status,
        idempotencyKey,
      })
    }, 400)
    return () => window.clearTimeout(timer)
  }, [
    amenities, bathrooms, bedrooms, currency, description, draftOwnerId, imageUrl,
    idempotencyKey, listingType, location, municipality, price, propertyType, province,
    sector, squareFeet, status, title,
  ])

  function discardDraft() {
    if (!window.confirm("¿Descartar este anuncio de propiedad sin terminar?")) return
    clearListingDraft(draftOwnerId)
    setTitle("")
    setDescription("")
    setImageUrl("")
    setPrice("")
    setCurrency("USD")
    setListingType("sale")
    setAmenities([])
    setLocation("")
    setProvince("")
    setMunicipality("")
    setSector("")
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
      setError("Seleccione un máximo de 8 fotos.")
      event.target.value = ""
      return
    }
    if (files.some((file) => !["image/jpeg", "image/png", "image/webp"].includes(file.type))) {
      setError("Todas las fotos deben estar en formato JPG, PNG o WebP.")
      event.target.value = ""
      return
    }
    if (files.some((file) => file.size > 5 * 1024 * 1024)) {
      setError("Cada foto debe pesar como máximo 5 MB.")
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
    if (!response.ok) throw new Error(getApiError(data, "No pudimos subir la imagen"))
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
      setError("Debe iniciar sesión para publicar una propiedad.")
      return
    }

    if (!imageFiles.length && !imageUrl.trim()) {
      setError("Agregue al menos una foto de la propiedad antes de publicar.")
      return
    }

    setError("")
    setLoading(true)
    const structuredLocation = buildDominicanLocation({ sector, municipality, province })
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
          location: structuredLocation,
          country_code: "DO",
          province,
          municipality,
          sector,
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
        throw new Error(getApiError(data, "No pudimos publicar la propiedad"))
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
      alert("¡Propiedad publicada correctamente!")
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
        <h1>Publicar una propiedad</h1>
        <p>Presente su propiedad de forma clara y profesional en HabitaRD.</p>
        {draftRestored && (
          <div className="draft-restored" role="status">
            <div>
              <strong>Borrador recuperado</strong>
              <p>Recuperamos los datos guardados. Vuelva a seleccionar las fotos.</p>
            </div>
            <button type="button" onClick={discardDraft}>Descartar borrador</button>
          </div>
        )}
        <form onSubmit={handleSubmit}>
          <div className="form-group">
            <label>Título</label>
            <input type="text" value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Hermosa vivienda familiar" required />
          </div>
          <div className="form-group">
            <label>Descripción (opcional)</label>
            <textarea value={description} onChange={(event) => setDescription(event.target.value)} placeholder="Describa la propiedad, el sector y sus características principales" rows="5" maxLength="2000" />
          </div>
          <div className="form-group">
            <label>Fotos de la propiedad</label>
            <label className="image-upload-button">
              Seleccionar fotos
              <input type="file" multiple accept="image/jpeg,image/png,image/webp" onChange={handleImageFiles} />
            </label>
            <span className="image-upload-help">Obligatorias · hasta 8 fotos JPG, PNG o WebP · 5 MB cada una · la primera será la portada</span>
            {imagePreviews.length > 0 && (
              <div className="image-preview-list">
                {imagePreviews.map((preview, index) => (
                  <span className="image-preview-item" key={preview}>
                    <img src={preview} alt={`Vista previa de la propiedad ${index + 1}`} />
                    <span>{index === 0 ? "Portada" : `Foto ${index + 1}`}</span>
                    {index > 0 && (
                      <button type="button" onClick={() => makeSelectedImageCover(index)}>
                        Usar como portada
                      </button>
                    )}
                    <button type="button" onClick={() => removeSelectedImage(index)}>
                      Eliminar
                    </button>
                  </span>
                ))}
                <button type="button" className="remove-image-button" onClick={clearSelectedImages}>Eliminar fotos</button>
              </div>
            )}
            <span className="image-or">o pegue el enlace de una imagen</span>
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
            <label>Modalidad</label>
            <select value={listingType} onChange={(event) => setListingType(event.target.value)}>
              <option value="sale">En venta</option><option value="rent">En alquiler</option>
            </select>
          </div>
          <div className="form-group">
            <label>Moneda</label>
            <select value={currency} onChange={(event) => setCurrency(event.target.value)}>
              <option value="USD">Dólares estadounidenses (US$)</option>
              <option value="DOP">Pesos dominicanos (RD$)</option>
            </select>
          </div>
          <div className="form-group"><label>{listingType === "rent" ? "Alquiler mensual" : "Precio de venta"}</label><input type="number" value={price} onChange={(event) => setPrice(event.target.value)} placeholder={listingType === "rent" ? "2200" : "350000"} required /></div>
          <div className="form-group">
            <label>Provincia o Distrito Nacional</label>
            <select value={province} onChange={(event) => setProvince(event.target.value)} required>
              <option value="">Seleccione una provincia</option>
              {DOMINICAN_PROVINCES.map((item) => <option value={item} key={item}>{item}</option>)}
            </select>
          </div>
          <div className="form-group">
            <label>Municipio o ciudad</label>
            <input type="text" value={municipality} onChange={(event) => setMunicipality(event.target.value)} placeholder="Santo Domingo" maxLength="100" required />
          </div>
          <div className="form-group">
            <label>Sector o vecindario (opcional)</label>
            <input type="text" value={sector} onChange={(event) => setSector(event.target.value)} placeholder="Piantini" maxLength="100" />
            <p className="location-help">Indique solamente el área pública. No publique una dirección residencial privada.</p>
            {(province || municipality || sector) && (
              <div className="location-map-preview">
                {!isMapLocationDetailed(buildDominicanLocation({ sector, municipality, province })) && (
                  <span>Agregue el municipio y la provincia para mejorar la búsqueda en el mapa.</span>
                )}
                <a href={buildPropertyMapUrl(buildDominicanLocation({ sector, municipality, province }))} target="_blank" rel="noreferrer">
                  Ver búsqueda en el mapa ↗
                </a>
              </div>
            )}
          </div>
          <div className="form-group">
            <label>Tipo de propiedad</label>
            <select value={propertyType} onChange={(event) => setPropertyType(event.target.value)} required>
              <option value="">Seleccione el tipo</option><option value="House">Casa</option><option value="Villa">Villa</option><option value="Apartment">Apartamento</option><option value="Condo">Condominio</option>
            </select>
          </div>
          <div className="form-group"><label>Habitaciones</label><input type="number" min="1" value={bedrooms} onChange={(event) => setBedrooms(event.target.value)} required /></div>
          <div className="form-group"><label>Baños</label><input type="number" min="0" max="100" value={bathrooms} onChange={(event) => setBathrooms(event.target.value)} required /></div>
          <div className="form-group"><label>Pies cuadrados (opcional)</label><input type="number" min="0" max="10000000" value={squareFeet} onChange={(event) => setSquareFeet(event.target.value)} placeholder="1800" /></div>
          <fieldset className="amenities-fieldset">
            <legend>Comodidades (opcional)</legend>
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
            <label>Estado</label>
            <select value={status} onChange={(event) => setStatus(event.target.value)}><option value="available">Disponible</option><option value="unavailable">No disponible</option></select>
          </div>
          {error && <p className="form-error">{error}</p>}
          <button type="submit" disabled={loading}>{loading ? "Publicando..." : "Publicar propiedad"}</button>
        </form>
      </div>
    </div>
  )
}

export default CreateProperty
