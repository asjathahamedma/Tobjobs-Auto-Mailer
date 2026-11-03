import { createClient } from "@/lib/supabase/browser";

const configuredApiBase = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "");
const apiBase =
  configuredApiBase || (process.env.NODE_ENV === "development" ? "http://localhost:8000" : "");

async function authenticatedFetch(path: string, init: RequestInit): Promise<Response> {
  const supabase = createClient();
  const { data, error } = await supabase.auth.getSession();
  if (error || !data.session) {
    throw new Error("Your session has expired. Sign in again.");
  }
  const headers = new Headers(init.headers);
  headers.set("Authorization", `Bearer ${data.session.access_token}`);
  if (init.body && !(init.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }
  try {
    return await fetch(`${apiBase}${path}`, {
      ...init,
      headers,
      cache: "no-store",
    });
  } catch (reason) {
    if (reason instanceof TypeError) {
      throw new Error("Could not reach the API. Check the backend service and API routing.");
    }
    throw reason;
  }
}

async function throwApiError(response: Response) {
  if (response.ok) return;
  const body = await response.text();
  let payload: { detail?: string } | null = null;
  try {
    payload = JSON.parse(body);
  } catch {
    payload = null;
  }
  const requestId = response.headers.get("x-request-id");
  let detail = payload?.detail;
  if (!detail || detail === "Internal Server Error") {
    detail = response.status >= 500
      ? "The API encountered an unexpected error. Check the backend runtime logs before retrying."
      : `Request failed (${response.status}).`;
  }
  throw new Error(requestId ? `${detail} (Reference: ${requestId})` : detail);
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await authenticatedFetch(path, init);
  await throwApiError(response);
  const payload = await response.json().catch(() => null);
  if (payload === null) {
    throw new Error("The API returned an invalid response.");
  }
  return payload as T;
}

export async function apiBlob(path: string): Promise<Blob> {
  const response = await authenticatedFetch(path, {});
  await throwApiError(response);
  return response.blob();
}

export function jsonBody(value: unknown): string {
  return JSON.stringify(value);
}
