// JWT storage. Kept in localStorage for simplicity in this reference build -
// for production, prefer an httpOnly cookie set by the backend so the token
// isn't reachable from JS at all (mitigates XSS token theft).
const TOKEN_KEY = "anpr_token";

export function saveToken(token: string) {
  if (typeof window !== "undefined") localStorage.setItem(TOKEN_KEY, token);
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function clearToken() {
  if (typeof window !== "undefined") localStorage.removeItem(TOKEN_KEY);
}
