// All requests use httpOnly session cookies (credentials: "include") —
// there is no Bearer token in JS-reachable storage, per security.py's
// design. Mutating requests must additionally echo the readable
// `csrf_token` cookie back as an `X-CSRF-Token` header (double-submit).

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

function csrfHeaders(): Record<string, string> {
  const token = readCookie("csrf_token");
  return token ? { "X-CSRF-Token": token } : {};
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail || detail;
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

export const api = {
  get: <T>(path: string): Promise<T> => fetch(path, { credentials: "include" }).then((r) => handle<T>(r)),
  post: <T>(path: string, body?: unknown): Promise<T> =>
    fetch(path, {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json", ...csrfHeaders() },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }).then((r) => handle<T>(r)),
  put: <T>(path: string, body?: unknown): Promise<T> =>
    fetch(path, {
      method: "PUT",
      credentials: "include",
      headers: { "Content-Type": "application/json", ...csrfHeaders() },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    }).then((r) => handle<T>(r)),
};

// Streams a POST response as newline-delimited "data: {...}" SSE frames —
// same async-generator pattern reused verbatim from every prior PoC's
// streaming features in this project series.
export async function* streamPost<T>(path: string, body: unknown): AsyncGenerator<T> {
  const res = await fetch(path, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...csrfHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok || !res.body) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || detail;
    } catch {
      /* ignore */
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
      if (!line.startsWith("data: ")) continue;
      yield JSON.parse(line.slice(6)) as T;
    }
  }
}
