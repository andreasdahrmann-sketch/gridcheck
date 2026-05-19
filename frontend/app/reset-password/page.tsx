"use client";

import { FormEvent, Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { ArrowLeft, Eye, EyeOff } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { isAuthInfrastructureError, resetPassword } from "@/lib/api/auth";
import { getPasswordPolicyChecks, isPasswordPolicySatisfied } from "@/lib/password-policy";

const cardClass = "rounded-[28px] border border-white/10 bg-bg-card/80 p-6 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";
const fieldClass =
  "h-11 rounded-xl border-border/70 bg-white/5 px-3 text-white placeholder:text-text-dim focus-visible:border-brand-cyan/70 focus-visible:ring-brand-cyan/20";

function ResetPasswordContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get("token") ?? searchParams.get("reset_token") ?? "";
  const [password, setPassword] = useState("");
  const [passwordConfirm, setPasswordConfirm] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const passwordChecks = useMemo(() => getPasswordPolicyChecks(password), [password]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (!token.trim()) {
      setError("Der Link ist ungueltig oder abgelaufen. Bitte fordern Sie einen neuen Link an.");
      return;
    }
    if (!isPasswordPolicySatisfied(password)) {
      setError(
        "Bitte ein Passwort mit mindestens 12 Zeichen sowie Gross-/Kleinbuchstaben, Zahl und Sonderzeichen verwenden."
      );
      return;
    }
    if (password !== passwordConfirm) {
      setError("Die Passwoerter stimmen nicht ueberein.");
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await resetPassword({ token: token.trim(), password });
      setMessage(result.message || "Passwort wurde aktualisiert. Sie koennen sich jetzt anmelden.");
      setTimeout(() => router.push("/login"), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Passwort konnte nicht gesetzt werden.");
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="mx-auto max-w-lg px-4 py-10 sm:px-6">
        <section className={cardClass}>
          <Link
            href="/login"
            className="inline-flex items-center gap-2 text-sm text-text-muted transition hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" aria-hidden />
            Zurueck zum Login
          </Link>
          <h1 className="mt-4 text-2xl font-semibold text-white">Neues Passwort setzen</h1>
          <p className="mt-2 text-sm leading-6 text-text-muted">
            Waehlen Sie ein sicheres Passwort fuer Ihr GridCheck-Konto.
          </p>

          {!token.trim() ? (
            <div className="mt-6 rounded-2xl border border-amber-400/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-100">
              Der Link ist ungueltig oder abgelaufen.{" "}
              <Link href="/login/forgot-password" className="font-medium text-brand-cyan hover:underline">
                Neuen Link anfordern
              </Link>
            </div>
          ) : (
            <form onSubmit={onSubmit} className="mt-6 space-y-4">
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <Label htmlFor="reset-password" className="text-white">
                    Neues Passwort
                  </Label>
                  <button
                    type="button"
                    onClick={() => setShowPassword((current) => !current)}
                    className="inline-flex items-center gap-1 text-xs font-medium text-text-muted transition hover:text-white"
                  >
                    {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                    {showPassword ? "Verbergen" : "Anzeigen"}
                  </button>
                </div>
                <Input
                  id="reset-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  className={fieldClass}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="reset-password-confirm" className="text-white">
                  Passwort wiederholen
                </Label>
                <Input
                  id="reset-password-confirm"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  className={fieldClass}
                  value={passwordConfirm}
                  onChange={(e) => setPasswordConfirm(e.target.value)}
                />
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                <p className="text-sm font-medium text-white">Passwort-Anforderungen</p>
                <ul className="mt-2 space-y-1 text-sm">
                  {passwordChecks.map((check) => (
                    <li key={check.label} className={check.ok ? "text-emerald-300" : "text-text-muted"}>
                      {check.ok ? "✓" : "○"} {check.label}
                    </li>
                  ))}
                </ul>
              </div>

              {message ? (
                <div className="rounded-2xl border border-emerald-400/30 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-200">
                  {message}
                </div>
              ) : null}
              {error ? (
                <div className="space-y-2">
                  <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                    {error}
                  </div>
                  {isAuthInfrastructureError(error) ? (
                    <p className="text-xs text-text-dim">
                      <Link href="/login/forgot-password" className="text-brand-cyan underline">
                        Neuen Link anfordern
                      </Link>
                    </p>
                  ) : null}
                </div>
              ) : null}

              <Button
                type="submit"
                disabled={isSubmitting}
                className="h-11 w-full rounded-xl bg-brand-orange text-white hover:bg-brand-orangeHover"
              >
                {isSubmitting ? "Wird gespeichert..." : "Passwort speichern"}
              </Button>
            </form>
          )}
        </section>
      </div>
    </main>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-bg text-white" />}>
      <ResetPasswordContent />
    </Suspense>
  );
}
