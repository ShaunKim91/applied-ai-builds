import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";

interface User {
  id: number;
  email: string;
  display_name: string;
  role: string;
  org_id: number;
}

interface AuthState {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  signup: (email: string, password: string, displayName: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthState | null>(null);

// The access-token cookie is short-lived (20 min, see backend config.py) —
// a silent background refresh keeps an active session alive without
// forcing a re-login.
const SILENT_REFRESH_MS = 15 * 60 * 1000;

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const tryLoadUser = async () => {
    try {
      const me = await api.get<User>("/api/auth/me");
      setUser(me);
      return true;
    } catch {
      return false;
    }
  };

  useEffect(() => {
    (async () => {
      const ok = await tryLoadUser();
      if (!ok) {
        try {
          await api.post("/api/auth/refresh");
          await tryLoadUser();
        } catch {
          setUser(null);
        }
      }
      setLoading(false);
    })();

    const interval = setInterval(() => {
      api.post("/api/auth/refresh").catch(() => setUser(null));
    }, SILENT_REFRESH_MS);
    return () => clearInterval(interval);
  }, []);

  const login = async (email: string, password: string) => {
    const result = await api.post<{ user: User }>("/api/auth/login", { email, password });
    setUser(result.user);
  };

  const signup = async (email: string, password: string, displayName: string) => {
    const result = await api.post<{ user: User }>("/api/auth/signup", { email, password, display_name: displayName });
    setUser(result.user);
  };

  const logout = async () => {
    await api.post("/api/auth/logout");
    setUser(null);
  };

  return <AuthContext.Provider value={{ user, loading, login, signup, logout }}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
