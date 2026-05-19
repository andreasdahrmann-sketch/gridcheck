/**
 * Trigger a file download from a Blob (desktop + mobile).
 * Defers revokeObjectURL so Safari/iOS can finish the download after async fetch.
 */
export function downloadBlobFile(blob: Blob, filename: string): void {
  if (typeof window === "undefined" || typeof document === "undefined") {
    return;
  }

  const safeName = filename.replace(/[^\w.\-()+äöüÄÖÜß ]+/g, "_") || "report.pdf";
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = safeName;
  link.rel = "noopener";
  link.style.display = "none";

  const mobile =
    typeof navigator !== "undefined" &&
    /iPhone|iPad|iPod|Android/i.test(navigator.userAgent);

  if (mobile) {
    link.target = "_blank";
  }

  document.body.appendChild(link);
  link.click();

  window.setTimeout(() => {
    URL.revokeObjectURL(url);
    link.remove();
  }, mobile ? 4_000 : 1_000);
}
