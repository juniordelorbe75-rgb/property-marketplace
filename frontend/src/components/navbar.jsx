import { useCallback, useEffect, useState } from "react"
import { Link, NavLink, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../utils/apiFetch"
import { readApiResponse } from "../utils/apiResponse"
import { INQUIRIES_CHANGED_EVENT } from "../utils/inquiryEvents"
import { normalizeUnreadInquiryCount } from "../utils/navbarStats"
import "./Navbar.css"

function NavigationLink({ to, children, end = false, onNavigate }) {
  return <NavLink className={({ isActive }) => isActive ? "nav-link active" : "nav-link"} end={end} onClick={onNavigate} to={to}>{children}</NavLink>
}

function Navbar() {
  const navigate = useNavigate()
  const { token, logout } = useAuth()
  const [unreadInquiries, setUnreadInquiries] = useState(0)
  const [adminToken, setAdminToken] = useState(null)
  const [menuOpen, setMenuOpen] = useState(false)

  const loadUnreadInquiries = useCallback(async (signal) => {
    if (!token) { setUnreadInquiries(0); return }
    try {
      const response = await apiFetch("/inquiries/unread-count", { headers: { Authorization: `Bearer ${token}` }, signal })
      const data = await readApiResponse(response)
      if (response.ok) setUnreadInquiries(normalizeUnreadInquiryCount(data))
    } catch (error) {
      if (error.name !== "AbortError") console.warn("Unread inquiry count is temporarily unavailable")
    }
  }, [token])

  useEffect(() => {
    const controller = new AbortController()
    const refresh = () => {
      if (document.visibilityState === "visible" && navigator.onLine !== false) {
        loadUnreadInquiries(controller.signal)
      }
    }
    refresh()
    const intervalId = window.setInterval(refresh, 45000)
    window.addEventListener(INQUIRIES_CHANGED_EVENT, refresh)
    window.addEventListener("focus", refresh)
    window.addEventListener("online", refresh)
    document.addEventListener("visibilitychange", refresh)
    return () => {
      controller.abort()
      window.clearInterval(intervalId)
      window.removeEventListener(INQUIRIES_CHANGED_EVENT, refresh)
      window.removeEventListener("focus", refresh)
      window.removeEventListener("online", refresh)
      document.removeEventListener("visibilitychange", refresh)
    }
  }, [loadUnreadInquiries])

  useEffect(() => {
    const controller = new AbortController()
    if (!token) return () => controller.abort()

    async function loadAdminAccess() {
      try {
        const response = await apiFetch("/reports/admin/access", {
          headers: { Authorization: `Bearer ${token}` },
          signal: controller.signal,
        })
        if (response.ok) setAdminToken(token)
        else setAdminToken(null)
      } catch (error) {
        if (error.name !== "AbortError") setAdminToken(null)
      }
    }

    loadAdminAccess()
    return () => controller.abort()
  }, [token])

  useEffect(() => {
    if (!menuOpen) return undefined

    function closeOnEscape(event) {
      if (event.key === "Escape") setMenuOpen(false)
    }

    window.addEventListener("keydown", closeOnEscape)
    return () => window.removeEventListener("keydown", closeOnEscape)
  }, [menuOpen])

  function closeMenu() { setMenuOpen(false) }
  async function handleLogout() {
    closeMenu()
    try {
      await apiFetch("/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
      })
    } catch {
      // Local sign-out must still complete if the network is unavailable.
    } finally {
      logout()
      navigate("/login")
    }
  }
  const isAdmin = Boolean(token && adminToken === token)

  return (
    <header className="site-header">
      <nav className="site-navigation" aria-label="Navegación principal">
        <div className="navigation-heading">
          <Link className="marketplace-brand" to="/" onClick={closeMenu} aria-label="Inicio de HabitaRD"><span aria-hidden="true">⌂</span><strong>HabitaRD</strong></Link>
          <button
            className="menu-button"
            type="button"
            aria-controls="primary-navigation-links"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((current) => !current)}
          >
            <span className="menu-button-icon" aria-hidden="true">{menuOpen ? "×" : "☰"}</span>
            <span>{menuOpen ? "Cerrar" : "Menú"}</span>
          </button>
        </div>
        <div className={`navigation-links${menuOpen ? " open" : ""}`} id="primary-navigation-links">
          <NavigationLink to="/search" onNavigate={closeMenu}>Buscar propiedades</NavigationLink>
          {token ? <>
            <NavigationLink to="/favorites" onNavigate={closeMenu}>Favoritos</NavigationLink>
            <NavigationLink to="/my-properties" onNavigate={closeMenu}>Mis anuncios</NavigationLink>
            <NavigationLink to="/inquiries" onNavigate={closeMenu}>Consultas{unreadInquiries > 0 && <span className="inquiry-badge" aria-label={`${unreadInquiries} mensajes de consulta sin leer`}>{unreadInquiries > 99 ? "99+" : unreadInquiries}</span>}</NavigationLink>
            <NavigationLink to="/create-property" onNavigate={closeMenu}>Publicar propiedad</NavigationLink>
            <NavigationLink to="/account" onNavigate={closeMenu}>Mi cuenta</NavigationLink>
            {isAdmin && <NavigationLink to="/safety-reports" onNavigate={closeMenu}>Seguridad</NavigationLink>}
            {isAdmin && <NavigationLink to="/data-sources" onNavigate={closeMenu}>Fuentes de datos</NavigationLink>}
            <button className="logout-button" type="button" onClick={handleLogout}>Cerrar sesión</button>
          </> : <>
            <NavigationLink to="/login" onNavigate={closeMenu}>Iniciar sesión</NavigationLink>
            <Link className="register-link" to="/register" onClick={closeMenu}>Crear cuenta</Link>
          </>}
        </div>
      </nav>
    </header>
  )
}

export default Navbar
