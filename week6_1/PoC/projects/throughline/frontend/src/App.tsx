import type { ReactNode } from "react";
import { Navigate, Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import Layout from "./components/Layout";
import { LangProvider } from "./i18n";
import Admin from "./pages/Admin";
import Cases from "./pages/Cases";
import Dashboard from "./pages/Dashboard";
import Landing from "./pages/Landing";
import Login from "./pages/Login";
import Workspace from "./pages/Workspace";
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
                path="/cases"
                element={
                  <Protected>
                    <Cases />
                  </Protected>
                }
              />
              <Route
                path="/cases/:caseId"
                element={
                  <Protected>
                    <Workspace />
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
