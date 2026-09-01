import { Link } from "react-router-dom"


function NotFound() {
  return (
    <main className="not-found-page">
      <p>404</p>
      <h1>Page not found</h1>
      <p>
        The page may have moved, or the address may be incorrect.
      </p>

      <div>
        <Link to="/">Browse Properties</Link>
        {" · "}
        <Link to="/account">My Account</Link>
      </div>
    </main>
  )
}

export default NotFound
