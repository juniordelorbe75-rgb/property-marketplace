import { Navigate, useLocation } from "react-router-dom"
import { useAuth } from "../context/AuthContext"
import { getReturnPath } from "../utils/authRedirect"


function ProtectedRoute({ children }) {
  const { token, sessionExpired } = useAuth()
  const location = useLocation()

  if (!token) {
    return <Navigate to="/login" replace state={{ returnTo: getReturnPath(location), sessionExpired }} />
  }

  return children
}

export default ProtectedRoute
