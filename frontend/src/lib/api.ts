/** API base: empty in dev (Vite proxy) or BACKEND_URL for production / cross-origin. */
export function apiUrl(path: string): string {
  const base = import.meta.env.VITE_BACKEND_URL?.replace(/\/$/, "") ?? "";
  const useProxy = import.meta.env.VITE_USE_API_PROXY === "true";
  if (useProxy || !base) {
    return path.startsWith("/") ? path : `/${path}`;
  }
  const normalized = path.startsWith("/") ? path : `/${path}`;
  return `${base}${normalized}`;
}
