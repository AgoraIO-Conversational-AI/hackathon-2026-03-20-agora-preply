const API_BASE = "/api/v1";

export class ApiError extends Error {
  constructor(
    public status: number,
    public statusText: string,
  ) {
    super(`API error: ${status} ${statusText}`);
    this.name = "ApiError";
  }
}

function getCsrfToken(): string {
  const match = document.cookie.match(/csrftoken=([^;]+)/);
  return match?.[1] ?? "";
}

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const csrfToken = getCsrfToken();
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrfToken,
      ...options?.headers,
    },
    ...options,
  });

  if (!response.ok) {
    throw new ApiError(response.status, response.statusText);
  }

  return response.json() as Promise<T>;
}

export { getCsrfToken, API_BASE };
