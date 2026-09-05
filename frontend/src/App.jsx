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
import PublicProfile from "./pages/PublicProfile"
import ForgotPassword from "./pages/ForgotPassword"
import ResetPassword from "./pages/ResetPassword"
import VerifyEmail from "./pages/VerifyEmail"
import Footer from "./components/Footer"
import TrustPage from "./pages/TrustPage"
import RouteMetadata from "./components/RouteMetadata"
import DataSources from "./pages/DataSources"

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
        <a className="skip-link" href="#contenido-principal">Saltar al contenido principal</a>
        <RouteMetadata />
        <Navbar />
        <ConnectionStatus />
        <LoginWelcome />

        <div id="contenido-principal" tabIndex={-1}>
          <Routes>
          <Route
            path="/"
            element={<Properties />}
          />

          <Route
            path="/search"
            element={<Properties searchMode />}
          />

          <Route
            path="/profiles/:id"
            element={<PublicProfile />}
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

          <Route path="/forgot-password" element={<ForgotPassword />} />
          <Route path="/reset-password" element={<ResetPassword />} />
          <Route path="/verify-email" element={<VerifyEmail />} />
          <Route path="/about" element={<TrustPage />} />
          <Route path="/data-partners" element={<TrustPage />} />
          <Route path="/privacy" element={<TrustPage />} />
          <Route path="/terms" element={<TrustPage />} />

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
            path="/data-sources"
            element={protectedPage(<DataSources />)}
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
        </div>
        <Footer />
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
