/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useEffect, useState } from "react"
import { AUTH_EXPIRED_EVENT } from "../utils/authSession"

const AuthContext = createContext()

export function AuthProvider({ children }) {
  const [token, setToken] = useState(
    localStorage.getItem("access_token")
  )
  const login = useCallback((accessToken) => {
    localStorage.setItem("access_token", accessToken)
    setToken(accessToken)
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem("access_token")
    setToken(null)
  }, [])

  useEffect(() => {
    function handleExpiredSession(event) {
      const currentToken = localStorage.getItem("access_token")

      if (currentToken && currentToken === event.detail?.token) {
        localStorage.removeItem("access_token")
        setToken(null)
      }
    }

    function handleStorage(event) {
      if (event.key === "access_token") {
        setToken(event.newValue)
      }
    }

    window.addEventListener(AUTH_EXPIRED_EVENT, handleExpiredSession)
    window.addEventListener("storage", handleStorage)

    return () => {
      window.removeEventListener(AUTH_EXPIRED_EVENT, handleExpiredSession)
      window.removeEventListener("storage", handleStorage)
    }
  }, [])

  return (
    <AuthContext.Provider
      value={{
        token,
        login,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
