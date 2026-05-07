export function getCsrfTokenFromCookie(): string | null {
  if (typeof document === "undefined") return null;
  const parts = document.cookie.split(";").map((entry) => entry.trim());
  const target = parts.find((entry) => entry.startsWith("gridcheck_csrf="));
  if (!target) return null;
  const value = target.split("=", 2)[1];
  return decodeURIComponent(value || "");
}
