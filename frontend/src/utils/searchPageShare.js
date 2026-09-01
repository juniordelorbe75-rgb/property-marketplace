import {
  buildPropertySearchParams,
  readPropertySearchParams,
} from "./propertySearchParams.js"

export function buildSearchPageShareUrl(currentUrl) {
  const url = new URL(currentUrl)
  const search = readPropertySearchParams(url.searchParams)
  url.pathname = "/"
  url.search = buildPropertySearchParams(search, search.page).toString()
  url.hash = ""
  return url.toString()
}

export async function shareSearchPage(capabilities, currentUrl) {
  const url = buildSearchPageShareUrl(currentUrl)
  const shareData = {
    title: "Property marketplace search",
    text: "View these property search results.",
    url,
  }

  if (typeof capabilities?.share === "function") {
    try {
      await capabilities.share(shareData)
      return { method: "native", url }
    } catch (error) {
      if (error?.name === "AbortError") return { method: "cancelled", url }
    }
  }

  if (typeof capabilities?.clipboard?.writeText === "function") {
    try {
      await capabilities.clipboard.writeText(url)
      return { method: "clipboard", url }
    } catch {
      // The caller can offer the canonical URL for manual copying.
    }
  }

  return { method: "manual", url }
}
