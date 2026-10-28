// Thin fetch wrapper: same-origin requests, CSRF double-submit header, active business header,
// and a typed ApiError carrying the backend's {"error": {code, message, details}} body.

const BUSINESS_KEY = "sp.businessId";
const UNSAFE_METHODS = new Set(["POST", "PUT", "PATCH", "DELETE"]);

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public details: Record<string, unknown> = {},
  ) {
    super(message);
  }

  get reasons(): string[] {
    const reasons = this.details?.reasons;
    return Array.isArray(reasons) ? (reasons as string[]) : [];
  }
}

export function getActiveBusinessId(): string | null {
  try {
    return window.localStorage.getItem(BUSINESS_KEY);
  } catch {
    return null;
  }
}

export function setActiveBusinessId(id: number | null): void {
  try {
    if (id === null) window.localStorage.removeItem(BUSINESS_KEY);
    else window.localStorage.setItem(BUSINESS_KEY, String(id));
  } catch {
    // storage unavailable (private mode); the session falls back to the first membership
  }
}

function readCookie(name: string): string | null {
  const match = document.cookie.split("; ").find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split("=").slice(1).join("=")) : null;
}

type Query = Record<string, string | number | boolean | null | undefined>;

export interface RequestOptions {
  method?: string;
  body?: unknown;
  query?: Query;
  headers?: Record<string, string>;
  form?: FormData;
}

function buildUrl(path: string, query?: Query): string {
  if (!query) return path;
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined && value !== null && value !== "") params.set(key, String(value));
  }
  const qs = params.toString();
  return qs ? `${path}?${qs}` : path;
}

export async function apiRequest<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const method = (options.method || "GET").toUpperCase();
  const headers: Record<string, string> = { Accept: "application/json", ...options.headers };
  const businessId = getActiveBusinessId();
  if (businessId) headers["X-Business-Id"] = businessId;
  if (UNSAFE_METHODS.has(method)) {
    const csrf = readCookie("sp_csrf");
    if (csrf) headers["X-CSRF-Token"] = csrf;
  }

  let body: BodyInit | undefined;
  if (options.form) {
    body = options.form;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }

  let response: Response;
  try {
    response = await fetch(buildUrl(path, options.query), { method, headers, body, credentials: "same-origin" });
  } catch {
    throw new ApiError(0, "network_error", "Cannot reach the server. Check your internet connection.");
  }

  const contentType = response.headers.get("content-type") || "";
  const data = contentType.includes("application/json") ? await response.json().catch(() => null) : await response.text();

  if (!response.ok) {
    const err = (data && typeof data === "object" && "error" in data ? (data as { error: any }).error : null) || {};
    throw new ApiError(
      response.status,
      err.code || "http_error",
      err.message || `Request failed (${response.status})`,
      err.details || {},
    );
  }
  return data as T;
}

export function newIdempotencyKey(): string {
  if (typeof crypto !== "undefined" && "randomUUID" in crypto) return crypto.randomUUID();
  return `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}
