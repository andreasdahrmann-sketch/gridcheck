export function safeNextPath(rawNext: string | null, fallback: string): string {
  if (!rawNext) return fallback;

  const trimmedNext = rawNext.trim();
  if (
    !trimmedNext.startsWith("/") ||
    trimmedNext.startsWith("//") ||
    trimmedNext.includes("\\") ||
    /[\u0000-\u001f\u007f]/.test(trimmedNext)
  ) {
    return fallback;
  }

  return trimmedNext;
}
