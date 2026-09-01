import { BrowserRouter, Routes, Route } from "react-router-dom"
import Navbar from "./components/Navbar"
import ConnectionStatus from "./components/ConnectionStatus"
import { AuthProvider } from "./context/AuthContext"

import Register from "./pages/Register"
import Account from "./pages/Account"
import Inquiries from "./pages/Inquiries"
import Properties from "./pages/Properties"
import Favorites from "./pages/Favorites"
import Login from "./pages/Login"
import PropertyDetails from "./pages/PropertyDetails"
import MyProperties from "./pages/MyProperties"
import CreateProperty from "./pages/CreateProperty"
import ProtectedRoute from "./components/ProtectedRoute"
import NotFound from "./pages/NotFound"

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
            path="*"
            element={<NotFound />}
          />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

export default App
