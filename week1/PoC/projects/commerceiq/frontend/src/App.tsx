import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import Admin from "./pages/Admin";
import CatalogVision from "./pages/CatalogVision";
import Dashboard from "./pages/Dashboard";
import Forecasting from "./pages/Forecasting";
import GenerativeStudio from "./pages/GenerativeStudio";
import Login from "./pages/Login";
import Search from "./pages/Search";

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <ProtectedRoute>
              <Layout>
                <Routes>
                  <Route path="/" element={<Dashboard />} />
                  <Route path="/vision" element={<CatalogVision />} />
                  <Route path="/generate" element={<GenerativeStudio />} />
                  <Route path="/forecast" element={<Forecasting />} />
                  <Route path="/search" element={<Search />} />
                  <Route
                    path="/admin"
                    element={
                      <ProtectedRoute adminOnly>
                        <Admin />
                      </ProtectedRoute>
                    }
                  />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </Layout>
            </ProtectedRoute>
          }
        />
      </Routes>
    </AuthProvider>
  );
}
