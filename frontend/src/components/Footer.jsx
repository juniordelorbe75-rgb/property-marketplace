import { Link } from "react-router-dom"
import "./Footer.css"

function Footer() {
  return (
    <footer className="site-footer">
      <div className="site-footer-inner">
        <div className="site-footer-identity">
          <strong>HabitaRD</strong>
          <span>Descubra propiedades en toda la República Dominicana.</span>
        </div>
        <nav aria-label="Información del mercado inmobiliario">
          <Link to="/about">Nosotros</Link>
          <Link to="/data-partners">Datos y aliados</Link>
          <Link to="/privacy">Privacidad</Link>
          <Link to="/terms">Términos</Link>
        </nav>
        <div className="site-footer-contact">
          <span>Preguntas, correcciones o solicitudes de retiro</span>
          <a href="mailto:juniordelorbe75@gmail.com">juniordelorbe75@gmail.com</a>
        </div>
      </div>
    </footer>
  )
}

export default Footer
