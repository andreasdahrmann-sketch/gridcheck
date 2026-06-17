import { redirect } from "next/navigation";
import { sanitizeAppRedirect } from "@/lib/safe-redirect";

type PageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

function pickParam(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

/** Legacy /auth/login links → /login. */
export default function AuthLoginRedirectPage({ searchParams }: PageProps) {
  const params = new URLSearchParams();
  const plan = pickParam(searchParams?.plan);
  const intent = pickParam(searchParams?.intent) ?? plan;
  const next = sanitizeAppRedirect(pickParam(searchParams?.next), "/projects");
  if (intent) params.set("intent", intent);
  if (plan) params.set("plan", plan);
  params.set("next", next);
  const qs = params.toString();
  redirect(qs ? `/login?${qs}` : "/login");
}
