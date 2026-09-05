const API_MESSAGE_TRANSLATIONS = {
  "Invalid or expired token": "La sesión no es válida o ha vencido",
  "User account no longer exists": "La cuenta de usuario ya no existe",
  "This session is no longer valid. Please log in again.": "Esta sesión ya no es válida. Inicie sesión nuevamente.",
  "Administrator access required": "Se requiere acceso administrativo",
  "Database is unavailable": "La base de datos no está disponible temporalmente",
  "User not found": "Usuario no encontrado",
  "Public profile not available": "El perfil público no está disponible",
  "Invalid email or password": "El correo o la contraseña no son válidos",
  "Email already registered": "Este correo ya está registrado",
  "Name cannot be empty": "El nombre no puede estar vacío",
  "Email cannot be empty": "El correo no puede estar vacío",
  "Current password is required to change your email": "Debe ingresar su contraseña actual para cambiar el correo",
  "Current password is incorrect": "La contraseña actual es incorrecta",
  "New password must be at least 8 characters": "La contraseña nueva debe tener al menos 8 caracteres",
  "New password must be different from current password": "La contraseña nueva debe ser diferente de la actual",
  "Create an account password before deleting your account": "Cree una contraseña para la cuenta antes de eliminarla",
  "Property not found": "Propiedad no encontrada",
  "You cannot report your own property": "No puede reportar su propia propiedad",
  "Safety report not found": "Reporte de seguridad no encontrado",
  "Choose a currency before filtering or sorting by price": "Seleccione una moneda antes de filtrar u ordenar por precio",
  "Minimum price cannot be greater than maximum price": "El precio mínimo no puede ser mayor que el precio máximo",
  "You do not own this property": "Esta propiedad no le pertenece",
  "You cannot favorite your own property": "No puede guardar su propia propiedad como favorita",
  "Property already favorited": "La propiedad ya está guardada en favoritos",
  "Favorite not found": "El favorito no fue encontrado",
  "This verification link is invalid or expired": "Este enlace de verificación no es válido o ha vencido",
  "You cannot send an inquiry about your own property": "No puede enviar una consulta sobre su propia propiedad",
  "This listing is temporarily unavailable during a safety review": "Este anuncio no está disponible temporalmente mientras se realiza una revisión de seguridad",
  "This property is not available for inquiries": "Esta propiedad no está disponible para recibir consultas",
  "You already have a pending inquiry for this property": "Ya tiene una consulta pendiente para esta propiedad",
  "Inquiry not found": "Consulta no encontrada",
  "You can only update inquiries you received": "Solo puede actualizar las consultas que recibió",
  "Invalid inquiry status": "El estado de la consulta no es válido",
  "Only pending inquiries can be updated": "Solo pueden actualizarse las consultas pendientes",
  "You can only cancel inquiries you sent": "Solo puede cancelar las consultas que envió",
  "Only pending inquiries can be cancelled": "Solo pueden cancelarse las consultas pendientes",
  "Closed inquiries cannot receive messages": "Las consultas cerradas no pueden recibir mensajes",
  "Message cannot be empty": "El mensaje no puede estar vacío",
  "This password reset link is invalid or expired": "Este enlace para restablecer la contraseña no es válido o ha vencido",
  "Choose a password you have not already used": "Elija una contraseña que no haya utilizado anteriormente",
  "Image data is invalid": "Los datos de la imagen no son válidos",
  "Image must be no larger than 5 MB": "La imagen debe pesar como máximo 5 MB",
  "File contents do not match the selected image type": "El contenido del archivo no coincide con el tipo de imagen seleccionado",
  "Image dimensions are too large": "Las dimensiones de la imagen son demasiado grandes",
  "Image is corrupt or cannot be decoded": "La imagen está dañada o no puede procesarse",
  "Upload not found": "Archivo subido no encontrado",
}

export function translateApiMessage(message) {
  return API_MESSAGE_TRANSLATIONS[message] || message
}

export function getApiError(data, fallbackMessage) {
  const detail = data?.detail
  const supportId = typeof data?.request_id === "string" && data.request_id
    ? ` Código de soporte: ${data.request_id}`
    : ""

  if (typeof detail === "string" && detail.trim()) {
    return `${translateApiMessage(detail)}${supportId}`
  }

  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => translateApiMessage(item?.msg))
      .filter(Boolean)

    if (messages.length > 0) {
      return `${messages.join(" ")}${supportId}`
    }
  }

  return `${fallbackMessage}${supportId}`
}
