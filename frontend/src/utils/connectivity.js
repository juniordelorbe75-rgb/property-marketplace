export function getConnectivityState(isOnline) {
  return isOnline === false ? "offline" : "online"
}

export function getConnectivityNotice(state) {
  if (state === "offline") {
    return {
      tone: "offline",
      message: "You appear to be offline. Loaded information is still available, but changes cannot be sent yet.",
    }
  }

  if (state === "restored") {
    return {
      tone: "restored",
      message: "Connection restored. You can safely continue.",
    }
  }

  return null
}
