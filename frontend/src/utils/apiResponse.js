function supportSuffix(response) {
  const requestId = response.headers.get("x-request-id")
  return requestId ? ` Support ID: ${requestId}` : ""
}

export async function readApiResponse(response) {
  const body = await response.text()

  if (!body.trim()) {
    if (response.status === 204) return null
    throw new Error(`The server returned an empty response. Please try again.${supportSuffix(response)}`)
  }

  try {
    return JSON.parse(body)
  } catch {
    throw new Error(`The server returned an invalid response. Please try again.${supportSuffix(response)}`)
  }
}
