export interface User {
  id: number;
  email: string;
  display_name: string;
  role: "user" | "admin";
}

const TOKEN_KEY = "parchment.token";

export function getToken(): string | null {
  try {
    return window.localStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null) {
  try {
    if (token) window.localStorage.setItem(TOKEN_KEY, token);
    else window.localStorage.removeItem(TOKEN_KEY);
  } catch {
    /* ignore */
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken();
  const headers = new Headers(options.headers);
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const res = await fetch(path, { ...options, headers, credentials: "include" });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body: body !== undefined ? JSON.stringify(body) : undefined }),
  postForm: <T>(path: string, form: FormData) => request<T>(path, { method: "POST", body: form }),
  patch: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "PATCH", body: body !== undefined ? JSON.stringify(body) : undefined }),
};

export async function login(email: string, password: string) {
  const data = await api.post<{ user: User; access_token: string }>("/api/auth/login", { email, password });
  setToken(data.access_token);
  return data.user;
}

export async function signup(email: string, password: string, display_name: string) {
  const data = await api.post<{ user: User; access_token: string }>("/api/auth/signup", {
    email,
    password,
    display_name,
  });
  setToken(data.access_token);
  return data.user;
}

export async function logout() {
  try {
    await api.post("/api/auth/logout");
  } finally {
    setToken(null);
  }
}

export async function fetchMe(): Promise<User | null> {
  if (!getToken()) return null;
  try {
    return await api.get<User>("/api/auth/me");
  } catch {
    setToken(null);
    return null;
  }
}
