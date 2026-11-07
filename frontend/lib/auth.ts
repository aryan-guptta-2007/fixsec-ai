/**
 * Session handling. The backend issues its own session token, so the user's
 * GitHub token never reaches the browser.
 */

const TOKEN_KEY = "fixsec_session";

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token);
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY);
}

export function logout(): void {
  clearToken();
  window.location.href = "/login";
}

/** After OAuth or demo sign-in the backend redirects with token in hash or query */
export function consumeTokenFromUrl(): void {
  if (typeof window === "undefined") return;
  const hashMatch = window.location.hash.match(/token=([^&]+)/);
  if (hashMatch) {
    setToken(decodeURIComponent(hashMatch[1]));
    window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
    return;
  }
  const searchToken = new URLSearchParams(window.location.search).get("token");
  if (searchToken) {
    setToken(searchToken);
    const cleanUrl = new URL(window.location.href);
    cleanUrl.searchParams.delete("token");
    window.history.replaceState({}, document.title, cleanUrl.pathname + cleanUrl.search + cleanUrl.hash);
  }
}
