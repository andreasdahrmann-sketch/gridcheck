const BASE = "/api/backend/api/v1/contact";

export async function submitContact(payload: {
  name: string;
  email: string;
  subject: string;
  message: string;
  website?: string;
}) {
  const res = await fetch(BASE, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body?.detail?.message ?? "Kontaktanfrage fehlgeschlagen");
  }
  return (await res.json()) as { status: string };
}
