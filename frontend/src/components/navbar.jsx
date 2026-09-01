import { useCallback, useEffect, useState } from "react"
import { Link, NavLink, useNavigate } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { apiFetch } from "../utils/apiFetch"
import { readApiResponse } from "../utils/apiResponse"
import { INQUIRIES_CHANGED_EVENT } from "../utils/inquiryEvents"
import { normalizePendingInquiryCount } from "../utils/navbarStats"
import "./Navbar.css"

function NavigationLink({ to, children, end = false, onNavigate }) {
  return <NavLink className={({ isActive }) => isActive ? "nav-link active" : "nav-link"} end={end} onClick={onNavigate} to={to}>{children}</NavLink>
}

function Navbar() {
  const navigate = useNavigate()
  const { token, logout } = useAuth()
  const [pendingInquiries, setPendingInquiries] = useState(0)
  const [menuOpen, setMenuOpen] = useState(false)

  const loadPendingInquiries = useCallback(async (signal) => {
    if (!token) { setPendingInquiries(0); return }
    try {
      const response = await apiFetch("/properties/my/stats", { headers: { Authorization: `Bearer ${token}` }, signal })
      const data = await readApiResponse(response)
      if (response.ok) setPendingInquiries(normalizePendingInquiryCount(data))
    } catch (error) {
      if (error.name !== "AbortError") console.warn("Pending inquiry count is temporarily unavailable")
    }
  }, [token])

  useEffect(() => {
    const controller = new AbortController()
    const refresh = () => loadPendingInquiries(controller.signal)
    refresh()
    window.addEventListener(INQUIRIES_CHANGED_EVENT, refresh)
    return () => { controller.abort(); window.removeEventListener(INQUIRIES_CHANGED_EVENT, refresh) }
  }, [loadPendingInquiries])

  useEffect(() => {
    if (!menuOpen) return undefined

    function closeOnEscape(event) {
      if (event.key === "Escape") setMenuOpen(false)
    }

    window.addEventListener("keydown", closeOnEscape)
    return () => window.removeEventListener("keydown", closeOnEscape)
  }, [menuOpen])

  function closeMenu() { setMenuOpen(false) }
  function handleLogout() { closeMenu(); logout(); navigate("/login") }

  return (
    <header className="site-header">
      <nav className="site-navigation" aria-label="Main navigation">
        <div className="navigation-heading">
          <Link className="marketplace-brand" to="/" onClick={closeMenu} aria-label="Property Marketplace home"><span aria-hidden="true">⌂</span><strong>Property Marketplace</strong></Link>
          <button
            className="menu-button"
            type="button"
            aria-controls="primary-navigation-links"
            aria-expanded={menuOpen}
            onClick={() => setMenuOpen((current) => !current)}
          >
            <span className="menu-button-icon" aria-hidden="true">{menuOpen ? "×" : "☰"}</span>
            <span>{menuOpen ? "Close" : "Menu"}</span>
          </button>
        </div>
        <div className={`navigation-links${menuOpen ? " open" : ""}`} id="primary-navigation-links">
          <NavigationLink to="/" end onNavigate={closeMenu}>Explore</NavigationLink>
          {token ? <>
            <NavigationLink to="/favorites" onNavigate={closeMenu}>Favorites</NavigationLink>
            <NavigationLink to="/my-properties" onNavigate={closeMenu}>My Listings</NavigationLink>
            <NavigationLink to="/inquiries" onNavigate={closeMenu}>Inquiries{pendingInquiries > 0 && <span className="inquiry-badge" aria-label={`${pendingInquiries} pending inquiries`}>{pendingInquiries > 99 ? "99+" : pendingInquiries}</span>}</NavigationLink>
            <NavigationLink to="/create-property" onNavigate={closeMenu}>Create Listing</NavigationLink>
            <NavigationLink to="/account" onNavigate={closeMenu}>Account</NavigationLink>
            <button className="logout-button" type="button" onClick={handleLogout}>Log out</button>
          </> : <>
            <NavigationLink to="/login" onNavigate={closeMenu}>Log in</NavigationLink>
            <Link className="register-link" to="/register" onClick={closeMenu}>Create account</Link>
          </>}
        </div>
      </nav>
    </header>
  )
}

export default Navbar
