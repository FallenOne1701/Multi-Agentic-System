import type { ApproveResponse, SessionResponse } from "./types";

function apiBase(): string {
  const base = process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") ?? "";
  return base;
}

async function parseError(res: Response): Promise<string> {
  try {
    const body = (await res.json()) as { detail?: string; message?: string };
    return body.detail ?? body.message ?? res.statusText;
  } catch {
    return res.statusText || `HTTP ${res.status}`;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const base = apiBase();
  if (!base) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL is not set. Point it at your backend API (no trailing slash).",
    );
  }
  const res = await fetch(`${base}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
  });
  if (!res.ok) {
    throw new Error(await parseError(res));
  }
  return res.json() as Promise<T>;
}

export function createComplaint(text: string): Promise<SessionResponse> {
  return request<SessionResponse>("/v1/complaints", {
    method: "POST",
    body: JSON.stringify({ text }),
  });
}

export function refineSession(
  id: string,
  pushback: string,
): Promise<SessionResponse> {
  return request<SessionResponse>(`/v1/sessions/${id}/refine`, {
    method: "POST",
    body: JSON.stringify({ pushback }),
  });
}

export function approveSession(id: string): Promise<ApproveResponse> {
  return request<ApproveResponse>(`/v1/sessions/${id}/approve`, {
    method: "POST",
    body: JSON.stringify({}),
  });
}

export function getSession(id: string): Promise<SessionResponse> {
  return request<SessionResponse>(`/v1/sessions/${id}`);
}
