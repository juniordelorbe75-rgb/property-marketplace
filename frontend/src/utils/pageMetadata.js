const STATIC_TITLES = new Map([
  ["/", "Propiedades en República Dominicana"],
  ["/search", "Buscar propiedades"],
  ["/login", "Iniciar sesión"],
  ["/register", "Crear una cuenta"],
  ["/forgot-password", "Recuperar contraseña"],
  ["/reset-password", "Restablecer contraseña"],
  ["/verify-email", "Verificar correo"],
  ["/account", "Mi cuenta"],
  ["/favorites", "Mis favoritos"],
  ["/my-properties", "Mis propiedades"],
  ["/create-property", "Publicar una propiedad"],
  ["/properties/new", "Publicar una propiedad"],
  ["/inquiries", "Mis mensajes"],
  ["/safety-reports", "Revisión de seguridad"],
  ["/data-sources", "Fuentes de datos"],
  ["/my-reports", "Mis reportes"],
  ["/about", "Acerca de HabitaRD"],
  ["/data-partners", "Fuentes y aliados de datos"],
  ["/privacy", "Privacidad"],
  ["/terms", "Términos de uso"],
  ["/auth/callback", "Completando inicio de sesión"],
])

export function pageTitleForPath(pathname) {
  const normalizedPath = pathname !== "/" ? pathname.replace(/\/+$/, "") : pathname
  const title = STATIC_TITLES.get(normalizedPath)
    || (/^\/properties\/[^/]+$/.test(normalizedPath) ? "Detalle de propiedad" : null)
    || (/^\/profiles\/[^/]+$/.test(normalizedPath) ? "Perfil público" : null)
    || "Página no encontrada"
  return `${title} | HabitaRD`
}
