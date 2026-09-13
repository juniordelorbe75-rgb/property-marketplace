import { useCallback, useEffect, useRef, useState } from "react"
import AppDialog from "./AppDialog"

function useAppDialog() {
  const [dialog, setDialog] = useState(null)
  const resolverRef = useRef(null)

  const closeDialog = useCallback((result) => {
    const resolve = resolverRef.current
    resolverRef.current = null
    setDialog(null)
    resolve?.(result)
  }, [])

  const openDialog = useCallback((configuration) => new Promise((resolve) => {
    resolverRef.current?.(false)
    resolverRef.current = resolve
    setDialog(configuration)
  }), [])

  useEffect(() => () => resolverRef.current?.(false), [])

  const confirmDialog = useCallback((configuration) => openDialog({
    mode: "confirm",
    ...configuration,
  }), [openDialog])

  const noticeDialog = useCallback((configuration) => openDialog({
    mode: "notice",
    ...configuration,
  }), [openDialog])

  return {
    confirmDialog,
    noticeDialog,
    dialogElement: <AppDialog dialog={dialog} onClose={closeDialog} />,
  }
}

export default useAppDialog
