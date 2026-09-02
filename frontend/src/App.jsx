import { BrowserRouter, Routes, Route } from "react-router-dom"
import Navbar from "./components/navbar"
import ConnectionStatus from "./components/ConnectionStatus"
import { AuthProvider } from "./context/AuthContext"

import Register from "./pages/register"
import Account from "./pages/account"
import Inquiries from "./pages/inquiries"
import Properties from "./pages/properties"
import Favorites from "./pages/favorites"
import Login from "./pages/login"
import PropertyDetails from "./pages/PropertyDetails"
import MyProperties from "./pages/MyProperties"
import CreateProperty from "./pages/CreateProperty"
import ProtectedRoute from "./components/ProtectedRoute"
import NotFound from "./pages/NotFound"
import SafetyReports from "./pages/SafetyReports"
import MySafetyReports from "./pages/MySafetyReports"
import OAuthCallback from "./pages/OAuthCallback"
import LoginWelcome from "./components/LoginWelcome"

function protectedPage(page) {
  return (
    <ProtectedRoute>
      {page}
    </ProtectedRoute>
  )
}

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Navbar />
        <ConnectionStatus />
        <LoginWelcome />

        <Routes>
          <Route
            path="/"
            element={<Properties />}
          />

          <Route
            path="/favorites"
            element={protectedPage(<Favorites />)}
          />

          <Route
            path="/account"
            element={protectedPage(<Account />)}
          />

          <Route
            path="/login"
            element={<Login />}
          />

          <Route
            path="/auth/callback"
            element={<OAuthCallback />}
          />

          <Route
            path="/register"
            element={<Register />}
          />

          <Route
            path="/properties/:id"
            element={<PropertyDetails />}
          />

          <Route
            path="/my-properties"
            element={protectedPage(<MyProperties />)}
          />

          <Route
            path="/create-property"
            element={protectedPage(<CreateProperty />)}
          />

          <Route
            path="/properties/new"
            element={protectedPage(<CreateProperty />)}
          />

          <Route
            path="/inquiries"
            element={protectedPage(<Inquiries />)}
          />

          <Route
            path="/safety-reports"
            element={protectedPage(<SafetyReports />)}
          />

          <Route
            path="/my-reports"
            element={protectedPage(<MySafetyReports />)}
          />

          <Route
            path="*"
            element={<NotFound />}
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
