export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const API_KEY = process.env.NEXT_PUBLIC_API_KEY ?? "changeme";

type HttpMethod = "GET" | "POST";

export async function apiRequest<T>(
  path: string,
  method: HttpMethod = "GET",
  body?: unknown,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    method,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: body ? JSON.stringify(body) : undefined,
    cache: "no-store",
  });

  if (!response.ok) {
    const maybeJson = await response.json().catch(() => ({}));
    const detail = maybeJson?.detail ?? "Falha ao processar requisição.";
    throw new Error(detail);
  }

  return (await response.json()) as T;
}
