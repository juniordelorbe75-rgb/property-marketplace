import { useEffect, useRef, useState } from "react"
import { getConnectivityNotice, getConnectivityState } from "../utils/connectivity"
import "./ConnectionStatus.css"

const RESTORED_NOTICE_MS = 5000

function ConnectionStatus() {
  const [connectionState, setConnectionState] = useState(
    () => getConnectivityState(navigator.onLine),
  )
  const restoreTimerRef = useRef(null)

  useEffect(() => {
    function clearRestoreTimer() {
      if (restoreTimerRef.current !== null) {
        window.clearTimeout(restoreTimerRef.current)
        restoreTimerRef.current = null
      }
    }

    function handleOffline() {
      clearRestoreTimer()
      setConnectionState("offline")
    }

    function handleOnline() {
      clearRestoreTimer()
      setConnectionState((current) => current === "offline" ? "restored" : "online")
      restoreTimerRef.current = window.setTimeout(() => {
        setConnectionState("online")
        restoreTimerRef.current = null
      }, RESTORED_NOTICE_MS)
    }

    window.addEventListener("offline", handleOffline)
    window.addEventListener("online", handleOnline)

    return () => {
      clearRestoreTimer()
      window.removeEventListener("offline", handleOffline)
      window.removeEventListener("online", handleOnline)
    }
  }, [])

  const notice = getConnectivityNotice(connectionState)
  if (!notice) return null

  return (
    <div
      className={`connection-status ${notice.tone}`}
      role="status"
      aria-live={notice.tone === "offline" ? "assertive" : "polite"}
    >
      <span aria-hidden="true">{notice.tone === "offline" ? "●" : "✓"}</span>
      <span>{notice.message}</span>
    </div>
  )
}

export default ConnectionStatus
