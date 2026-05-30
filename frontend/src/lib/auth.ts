/**
 * JWT-based auth for AtlasLens.
 *
 * Login flow:
 *  - POST /api/auth/login {email, password} -> {access_token, user}
 *  - Token persisted in localStorage as "atlaslens.token"
 *  - All API clients send `Authorization: Bearer <token>`
 *  - 401 from the backend automatically clears the token and forces a re-login.
 */

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export interface CurrentUser {
  email: string;
  name: string;
  identity_provider: string;
  member_id: string;
  role: "em" | "member" | "admin";
  profile: {
    id: string;
    name: string;
    role: string;
    title: string;
    joined_at: string;
    manager_id: string | null;
    skills: string[];
    interests: string[];
    bio: string;
  } | null;
}

interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_at: string;
  user: CurrentUser;
}

const TOKEN_KEY = "atlaslens.token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

const BASE = import.meta.env.VITE_API_BASE ?? "";

export async function authedFetch<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const token = getToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init.headers as Record<string, string>) ?? {}),
  };
  if (token) headers["Authorization"] = `Bearer ${token}`;
  const res = await fetch(`${BASE}${path}`, { ...init, headers });
  if (res.status === 401) {
    setToken(null);
    // Force a reload — App.tsx will re-render and show the login page.
    if (typeof window !== "undefined") window.location.reload();
    throw new Error("unauthenticated");
  }
  if (!res.ok) {
    let body = "";
    try {
      body = await res.text();
    } catch {
      /* ignore */
    }
    throw new Error(`${path} ${res.status}: ${body || res.statusText}`);
  }
  if (res.status === 204) {
    return undefined as T;
  }
  const text = await res.text();
  if (!text) {
    return undefined as T;
  }
  return JSON.parse(text) as T;
}

async function fetchMe(): Promise<CurrentUser | null> {
  if (!getToken()) return null;
  try {
    return await authedFetch<CurrentUser>("/api/auth/me");
  } catch {
    return null;
  }
}

export function useCurrentUser() {
  return useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchMe,
    retry: false,
    staleTime: 60_000,
  });
}

export function useLogin() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: { email: string; password: string }) => {
      const res = await fetch(`${BASE}/api/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(detail.detail || "login failed");
      }
      const data = (await res.json()) as LoginResponse;
      setToken(data.access_token);
      return data;
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["auth", "me"] });
    },
  });
}

export function logout() {
  setToken(null);
  if (typeof window !== "undefined") window.location.assign("/");
}
