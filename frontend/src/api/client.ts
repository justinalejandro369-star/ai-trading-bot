/**
 * API client with credentials: 'include' for cookie-based JWT auth.
 * BASE_URL is empty — Vite proxy handles /api and /auth prefixes.
 */

const BASE_URL = ''

export async function apiFetch(
  path: string,
  init?: RequestInit,
): Promise<Response> {
  const response = await fetch(`${BASE_URL}${path}`, {
    ...init,
    credentials: 'include',
  })
  return response
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await apiFetch(path)
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const response = await apiFetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (!response.ok) {
    throw new Error(`POST ${path} failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}
