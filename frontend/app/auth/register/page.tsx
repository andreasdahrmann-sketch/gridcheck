import { redirect } from "next/navigation";

type PageProps = {
  searchParams?: Record<string, string | string[] | undefined>;
};

function pickParam(value: string | string[] | undefined): string | undefined {
  if (Array.isArray(value)) return value[0];
  return value;
}

/** Legacy /auth/register links → /register (plan/intent query preserved). */
export default function AuthRegisterRedirectPage({ searchParams }: PageProps) {
  const params = new URLSearchParams();
  const plan = pickParam(searchParams?.plan);
  const intent = pickParam(searchParams?.intent) ?? plan;
  const next = pickParam(searchParams?.next);
  if (intent) params.set("intent", intent);
  if (plan) params.set("plan", plan);
  if (next) params.set("next", next);
  const qs = params.toString();
  redirect(qs ? `/register?${qs}` : "/register");
}
