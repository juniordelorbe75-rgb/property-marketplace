import { useEffect } from "react"
import { useLocation } from "react-router-dom"

import { pageTitleForPath } from "../utils/pageMetadata.js"

function RouteMetadata() {
  const { pathname } = useLocation()

  useEffect(() => {
    document.title = pageTitleForPath(pathname)
  }, [pathname])

  return null
}

export default RouteMetadata
