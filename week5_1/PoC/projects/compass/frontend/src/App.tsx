import { Navigate, Route, Routes } from "react-router-dom";

import { AuthProvider } from "./auth/AuthContext";
import { Layout } from "./components/Layout";
import { ProtectedRoute } from "./components/ProtectedRoute";
import Admin from "./pages/Admin";
import Archive from "./pages/Archive";
import Dashboard from "./pages/Dashboard";
import GroundingLab from "./pages/GroundingLab";
import Login from "./pages/Login";
import Research from "./pages/Research";
import TrendRadar from "./pages/TrendRadar";

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
                  <Route path="/research" element={<Research />} />
                  <Route path="/archive" element={<Archive />} />
                  <Route path="/grounding-lab" element={<GroundingLab />} />
                  <Route path="/trend-radar" element={<TrendRadar />} />
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
