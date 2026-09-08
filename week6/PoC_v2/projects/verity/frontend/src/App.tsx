import type { ReactNode } from "react";
import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import Layout from "./components/Layout";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import { LangProvider } from "./i18n";
import Admin from "./pages/Admin";
import Archive from "./pages/Archive";
import CatEvents from "./pages/CatEvents";
import Dashboard from "./pages/Dashboard";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Radar from "./pages/Radar";
import Research from "./pages/Research";
import { ThemeProvider } from "./theme/ThemeContext";

function Root() {
  const { user, loading } = useAuth();
  if (loading) return null;
  return user ? (
    <Layout>
      <Dashboard />
    </Layout>
  ) : (
    <Landing />
  );
}

function Protected({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  return <Layout>{children}</Layout>;
}

function AdminOnly({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== "admin") return <Navigate to="/" replace />;
  return <Layout>{children}</Layout>;
}

function AuthPage() {
  const { user, loading } = useAuth();
  if (loading) return null;
  if (user) return <Navigate to="/" replace />;
  return <Login />;
}

export default function App() {
  return (
    <LangProvider>
      <ThemeProvider>
        <Router>
          <AuthProvider>
            <Routes>
              <Route path="/" element={<Root />} />
              <Route path="/login" element={<AuthPage />} />
              <Route path="/signup" element={<AuthPage />} />
              <Route
                path="/research"
                element={
                  <Protected>
                    <Research />
                  </Protected>
                }
              />
              <Route
                path="/archive"
                element={
                  <Protected>
                    <Archive />
                  </Protected>
                }
              />
              <Route
                path="/cat-events"
                element={
                  <Protected>
                    <CatEvents />
                  </Protected>
                }
              />
              <Route
                path="/radar"
                element={
                  <Protected>
                    <Radar />
                  </Protected>
                }
              />
              <Route
                path="/admin"
                element={
                  <AdminOnly>
                    <Admin />
                  </AdminOnly>
                }
              />
            </Routes>
          </AuthProvider>
        </Router>
      </ThemeProvider>
    </LangProvider>
  );
}
