const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "/api/v1";

let accessToken: string | null = null;

export function setAccessToken(token: string | null): void {
  accessToken = token;
}

export function getAccessToken(): string | null {
  return accessToken;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export const SESSION_EXPIRED_EVENT = "parksight:session-expired";

export async function apiFetch(
  path: string,
  options: RequestInit = {},
): Promise<Response> {
  const headers = new Headers(options.headers);

  if (accessToken) {
    headers.set("Authorization", `Bearer ${accessToken}`);
  }

  const requestToken = accessToken;

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    cache: "no-store",
  });

  if (
    response.status === 401 &&
    requestToken !== null &&
    accessToken === requestToken &&
    !path.startsWith("/auth/")
  ) {
    setAccessToken(null);
    window.dispatchEvent(new Event(SESSION_EXPIRED_EVENT));
  }

  if (!response.ok) {
    const body: unknown = await response.json().catch(() => null);

    let message = `Request failed: HTTP ${response.status}`;

    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;

      if (typeof detail === "string") {
        message = detail;
      }
    }

    throw new ApiError(response.status, message);
  }

  return response;
}
