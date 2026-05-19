"use client";

import { Suspense, FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Eye, EyeOff, ShieldCheck } from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { isAuthInfrastructureError, login } from "@/lib/api/auth";
import {
  isSelfServeCheckoutPlan,
  normalizeCheckoutPlan,
  offerIdForCheckoutPlan,
  settingsCheckoutHref,
} from "@/lib/billing-plans";
import { getPurchaseIntentProfile, normalizePurchaseIntent } from "@/lib/purchase-intents";

const cardClass = "rounded-[28px] border border-white/10 bg-bg-card/80 p-6 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";
const fieldClass =
  "h-11 rounded-xl border-border/70 bg-white/5 px-3 text-white placeholder:text-text-dim focus-visible:border-brand-cyan/70 focus-visible:ring-brand-cyan/20";

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const resetToken = searchParams.get("reset_token");

  useEffect(() => {
    if (resetToken) {
      router.replace(`/reset-password?token=${encodeURIComponent(resetToken)}`);
    }
  }, [resetToken, router]);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const checkoutPlan = normalizeCheckoutPlan(searchParams.get("plan"));
  const intent = normalizePurchaseIntent(searchParams.get("intent") ?? checkoutPlan);
  const intentProfile = getPurchaseIntentProfile(intent);
  const defaultNext =
    checkoutPlan && isSelfServeCheckoutPlan(checkoutPlan)
      ? settingsCheckoutHref(checkoutPlan)
      : intent === "upgrade" || intent === "pro"
        ? "/settings"
        : "/projects";
  const nextTarget = searchParams.get("next") || defaultNext;
  const registerParams = new URLSearchParams({ intent, next: nextTarget });
  if (checkoutPlan) registerParams.set("plan", checkoutPlan);
  const registerHref = `/register?${registerParams.toString()}`;
  const contactHref = `/contact?intent=${encodeURIComponent(intent)}`;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !password) {
      setError("Bitte E-Mail und Passwort eingeben.");
      return;
    }

    setIsSubmitting(true);
    try {
      await login({ email: email.trim(), password });
      window.location.href = nextTarget;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login fehlgeschlagen");
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="mx-auto max-w-5xl px-4 py-6 sm:px-6 sm:py-10">
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)]">
          <section className="space-y-6">
            <div className="rounded-[28px] border border-white/10 bg-white/5 p-6">
              <div className="inline-flex rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-brand-cyan">
                Konto-Zugang
              </div>
              <h1 className="mt-4 text-3xl font-semibold text-white">
                Login fuer gespeicherte Checks, Projekte und Upgrade-Pfade
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
                Nach dem Login werden Analysen Ihrem Konto, Ihrer History und Ihren Projekten revisionssicher zugeordnet.
                So bleibt klar, welcher Run mit welchem Paket und welchem Scope erstellt wurde.
              </p>
            </div>

            <div className="rounded-[24px] border border-brand-cyan/20 bg-brand-cyan/10 p-5">
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-white">
                  {intentProfile.badge}
                </span>
                <span className="text-sm font-semibold text-white">{intentProfile.label}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-white/90">{intentProfile.summary}</p>
              <p className="mt-2 text-xs leading-5 text-text-muted">Naechster Schritt nach Login: {intentProfile.nextStep}</p>
              {checkoutPlan && offerIdForCheckoutPlan(checkoutPlan) ? (
                <p className="mt-2 text-xs leading-5 text-brand-cyan">
                  Gewaehltes Paket: {checkoutPlan}. Nach dem Login wird Stripe Checkout gestartet.
                </p>
              ) : null}
              <div className="mt-4 flex flex-col gap-2 sm:flex-row">
                <Link
                  href="/projektierer"
                  className="inline-flex items-center justify-center rounded-xl bg-brand-orange px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-orangeHover"
                >
                  Direkt zum Projektierer-Modul
                </Link>
                <Link
                  href={contactHref}
                  className="inline-flex items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
                >
                  Anfragepfad oeffnen
                </Link>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Free Einstieg</p>
                <p className="mt-2 text-sm text-white">Bis zu 3 kostenlose Checks fuer den ersten Produktfit.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Revisionssichere History</p>
                <p className="mt-2 text-sm text-white">Runs, Paketkontext und Revisionen bleiben im Konto nachvollziehbar.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Klare Kaufpfade</p>
                <p className="mt-2 text-sm text-white">Self-Serve, Pro, Professional, Express und VNB Pilot bleiben getrennt.</p>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-white">
                  <CheckCircle2 className="h-4 w-4 text-brand-cyan" />
                  Weiterleitung mit Zielkontext
                </p>
                <p className="mt-2 text-sm leading-6 text-text-muted">
                  Nach dem Login geht es direkt weiter zu{" "}
                  <span className="font-medium text-white">
                    {nextTarget === "/settings" ? "Tarife & Analyse-History" : "Ihren Projekten"}
                  </span>
                  .
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-white">
                  <ShieldCheck className="h-4 w-4 text-brand-orange" />
                  Fachlich sauberer Kontobezug
                </p>
                <p className="mt-2 text-sm leading-6 text-text-muted">
                  Checks, Paketpfade und Verlauf bleiben einem klaren Nutzerkonto statt einer losen Session zugeordnet.
                </p>
              </div>
            </div>
          </section>

          <section className={cardClass}>
            <h2 className="text-2xl font-semibold text-white">Login</h2>
            <p className="mt-2 text-sm leading-6 text-text-muted">
              Nutzen Sie Ihr Konto fuer Projekte, Analyse-History und den passenden Upgrade- oder Servicepfad.
            </p>

            <form onSubmit={onSubmit} className="mt-6 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="login-email" className="text-white">
                  E-Mail
                </Label>
                <Input
                  id="login-email"
                  type="email"
                  autoComplete="email"
                  className={fieldClass}
                  placeholder="name@firma.de"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between gap-3">
                  <Label htmlFor="login-password" className="text-white">
                    Passwort
                  </Label>
                  <div className="flex items-center gap-3">
                    <Link
                      href="/login/forgot-password"
                      className="text-xs font-medium text-brand-cyan transition hover:text-brand-cyan/80"
                    >
                      Passwort vergessen?
                    </Link>
                    <button
                      type="button"
                      onClick={() => setShowPassword((current) => !current)}
                      className="inline-flex items-center gap-1 text-xs font-medium text-text-muted transition hover:text-white"
                    >
                      {showPassword ? <EyeOff className="h-3.5 w-3.5" /> : <Eye className="h-3.5 w-3.5" />}
                      {showPassword ? "Verbergen" : "Anzeigen"}
                    </button>
                  </div>
                </div>
                <Input
                  id="login-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  className={fieldClass}
                  placeholder="Ihr Passwort"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

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
                      . Vercel: BACKEND_URL=https://gridcheck-production.up.railway.app — siehe docs/LAUNCH.md.
                    </p>
                  ) : null}
                </div>
              ) : null}

              <Button
                type="submit"
                disabled={isSubmitting}
                className="h-11 w-full rounded-xl bg-brand-orange text-white hover:bg-brand-orangeHover"
              >
                {isSubmitting ? "Loggt ein..." : "Einloggen"}
              </Button>
            </form>

            <div className="mt-5 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-text-muted">
              Nach erfolgreichem Login geht es weiter zu{" "}
              <span className="font-medium text-white">
                {nextTarget === "/settings" ? "Tarif & Analyse-History" : "Ihren Projekten"}
              </span>
              . Wenn Sie erst pruefen wollen, koennen Sie den{" "}
              <Link className="font-medium text-brand-cyan" href="/projektierer">
                Projektierer-Check
              </Link>{" "}
              jederzeit direkt aufrufen.
            </div>

            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <Button asChild className="h-11 rounded-xl bg-brand-cyan text-slate-950 hover:bg-brand-cyan/90">
                <Link href={registerHref}>
                  Registrierung starten
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" className="h-11 rounded-xl border-white/15 bg-transparent text-white hover:bg-white/5">
                <Link href={contactHref}>Anfrage statt Login</Link>
              </Button>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-bg text-white" />}>
      <LoginPageContent />
    </Suspense>
  );
}
