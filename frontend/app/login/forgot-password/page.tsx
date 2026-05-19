"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { isAuthInfrastructureError, requestPasswordReset } from "@/lib/api/auth";

const cardClass = "rounded-[28px] border border-white/10 bg-bg-card/80 p-6 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";
const fieldClass =
  "h-11 rounded-xl border-border/70 bg-white/5 px-3 text-white placeholder:text-text-dim focus-visible:border-brand-cyan/70 focus-visible:ring-brand-cyan/20";

function ForgotPasswordContent() {
  const [email, setEmail] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [message, setMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);

    if (!email.trim()) {
      setError("Bitte geben Sie Ihre E-Mail-Adresse ein.");
      return;
    }

    setIsSubmitting(true);
    try {
      const result = await requestPasswordReset(email.trim());
      setMessage(
        result.message ||
          "Falls ein Konto mit dieser E-Mail existiert, erhalten Sie in Kuerze eine Nachricht mit weiteren Schritten."
      );
      setEmail("");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Anfrage konnte nicht gesendet werden.");
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
          <h1 className="mt-4 text-2xl font-semibold text-white">Passwort zuruecksetzen</h1>
          <p className="mt-2 text-sm leading-6 text-text-muted">
            Geben Sie die E-Mail Ihres Kontos ein. Sie erhalten – sofern ein Konto existiert – einen Link zum Setzen
            eines neuen Passworts.
          </p>

          <form onSubmit={onSubmit} className="mt-6 space-y-4">
            <div className="space-y-2">
              <Label htmlFor="forgot-email" className="text-white">
                E-Mail
              </Label>
              <Input
                id="forgot-email"
                type="email"
                autoComplete="email"
                className={fieldClass}
                placeholder="name@firma.de"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
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
                    Diagnose:{" "}
                    <Link href="/api-test" className="text-brand-cyan underline">
                      /api-test
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
              {isSubmitting ? "Wird gesendet..." : "Link anfordern"}
            </Button>
          </form>

          <p className="mt-5 text-sm text-text-muted">
            Kein Zugang mehr noetig?{" "}
            <Link href="/login" className="font-medium text-brand-cyan hover:underline">
              Zum Login
            </Link>
          </p>
        </section>
      </div>
    </main>
  );
}

export default function ForgotPasswordPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-bg text-white" />}>
      <ForgotPasswordContent />
    </Suspense>
  );
}
