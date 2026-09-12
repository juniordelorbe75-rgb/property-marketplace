function supportSuffix(response) {
  const requestId = response.headers.get("x-request-id")
  return requestId ? ` Código de soporte: ${requestId}` : ""
}

export async function readApiResponse(response) {
  const body = await response.text()

  if (!body.trim()) {
    if (response.status === 204) return null
    throw new Error(`El servidor devolvió una respuesta vacía. Intente de nuevo.${supportSuffix(response)}`)
  }

  try {
    return JSON.parse(body)
  } catch {
    throw new Error(`El servidor devolvió una respuesta no válida. Intente de nuevo.${supportSuffix(response)}`)
  }
}
