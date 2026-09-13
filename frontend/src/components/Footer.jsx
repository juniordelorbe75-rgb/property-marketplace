import { Link } from "react-router-dom"
import "./Footer.css"

function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="site-footer-identity">
          <div className="site-footer-brand">
            <img src="/habitard-logo.jpeg" alt="" width="48" height="48" />
            <strong>HabitaRD</strong>
          </div>
          <span>Descubra propiedades en toda la República Dominicana.</span>
        </div>
        <div className="site-footer-links">
          <nav aria-label="Información sobre HabitaRD">
            <strong>Información</strong>
            <Link to="/about">Nosotros</Link>
            <Link to="/terms">Términos</Link>
            <Link to="/privacy">Privacidad</Link>
          </nav>
          <nav aria-label="Datos y contacto">
            <strong>Conexión</strong>
            <Link to="/data-partners">Datos y aliados</Link>
            <Link to="/contact">Contacto</Link>
          </nav>
        </div>
      </div>
    </footer>
  )
}

export default Footer
