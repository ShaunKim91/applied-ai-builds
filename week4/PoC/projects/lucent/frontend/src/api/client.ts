export interface User {
  id: number;
  email: string;
  display_name: string;
  role: "user" | "admin";
}

const TOKEN_KEY = "lucent.token";

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

/**
 * Consumes a POST endpoint that streams Server-Sent-Events-shaped lines
 * (`data: {...}\n\n`) — used for the chat endpoint. A plain GET-only
 * `EventSource` can't carry a POST body, so this reads the raw
 * `ReadableStream` from `fetch()` directly and parses SSE framing by hand.
 * Yields one parsed JSON object per `data:` line as it arrives.
 */
export async function* streamPost<T = Record<string, unknown>>(path: string, body: unknown): AsyncGenerator<T> {
  const token = getToken();
  const headers = new Headers({ "Content-Type": "application/json" });
  if (token) headers.set("Authorization", `Bearer ${token}`);

  const res = await fetch(path, { method: "POST", headers, body: JSON.stringify(body), credentials: "include" });
  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      detail = (await res.json()).detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new Error(detail);
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n\n");
    buffer = lines.pop() ?? "";
    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed.startsWith("data: ")) continue;
      yield JSON.parse(trimmed.slice("data: ".length)) as T;
    }
  }
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
