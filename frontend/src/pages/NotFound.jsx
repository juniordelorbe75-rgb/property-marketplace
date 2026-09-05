import { Link } from "react-router-dom"


function NotFound() {
  return (
    <main className="not-found-page">
      <p>404</p>
      <h1>Página no encontrada</h1>
      <p>
        Es posible que la página haya cambiado de ubicación o que la dirección sea incorrecta.
      </p>

      <div>
        <Link to="/">Explorar propiedades</Link>
        {" · "}
        <Link to="/account">Mi cuenta</Link>
      </div>
    </main>
  )
}

export default NotFound
