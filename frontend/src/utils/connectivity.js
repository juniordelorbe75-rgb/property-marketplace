export function getConnectivityState(isOnline) {
  return isOnline === false ? "offline" : "online"
}

export function getConnectivityNotice(state) {
  if (state === "offline") {
    return {
      tone: "offline",
      message: "Parece que no tiene conexión. La información cargada sigue disponible, pero los cambios todavía no pueden enviarse.",
    }
  }

  if (state === "restored") {
    return {
      tone: "restored",
      message: "Conexión restablecida. Puede continuar con seguridad.",
    }
  }

  return null
}
