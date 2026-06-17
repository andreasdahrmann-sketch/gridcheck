"use client";

import { FormEvent, Suspense, useMemo, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Eye, EyeOff, UserRound } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { isAuthInfrastructureError, login, register } from "@/lib/api/auth";
import { getPasswordPolicyChecks, isPasswordPolicySatisfied } from "@/lib/password-policy";
import {
  isSelfServeCheckoutPlan,
  normalizeCheckoutPlan,
  offerIdForCheckoutPlan,
  settingsCheckoutHref,
} from "@/lib/billing-plans";
import { getPurchaseIntentProfile, normalizePurchaseIntent } from "@/lib/purchase-intents";
import { formSelectClass as selectClass } from "@/lib/form-classes";
import { sanitizeAppRedirect } from "@/lib/safe-redirect";

const cardClass = "rounded-[28px] border border-white/10 bg-bg-card/80 p-6 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";
const fieldClass =
  "h-11 rounded-xl border-border/70 bg-white/5 px-3 text-white placeholder:text-text-dim focus-visible:border-brand-cyan/70 focus-visible:ring-brand-cyan/20";

function RegisterPageContent() {
  const searchParams = useSearchParams();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
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
        : "/onboarding";
  const nextTarget = sanitizeAppRedirect(searchParams.get("next"), defaultNext);
  const loginParams = new URLSearchParams({ intent, next: nextTarget });
  if (checkoutPlan) loginParams.set("plan", checkoutPlan);
  const loginHref = `/login?${loginParams.toString()}`;
  const [role, setRole] = useState(intent === "vnb-pilot" ? "netzbetreiber" : "projektierer");

  const passwordChecks = useMemo(() => getPasswordPolicyChecks(password), [password]);
  const formChecks = useMemo(
    () => [
      ...passwordChecks,
      { label: "E-Mail angegeben", ok: email.trim().length > 0 },
      { label: "Rolle ausgewaehlt", ok: role.trim().length > 0 },
    ],
    [email, passwordChecks, role]
  );

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);

    if (!email.trim() || !isPasswordPolicySatisfied(password)) {
      setError(
        "Bitte E-Mail angeben und ein Passwort mit mindestens 12 Zeichen sowie Gross-/Kleinbuchstaben, Zahl und Sonderzeichen verwenden."
      );
      return;
    }

    setIsSubmitting(true);
    try {
      await register({ email: email.trim(), password, role, full_name: fullName.trim() || undefined });
      await login({ email: email.trim(), password });
      window.location.href = nextTarget;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Registrierung fehlgeschlagen";
      setError(msg);
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
                Konto anlegen
              </div>
              <h1 className="mt-4 text-3xl font-semibold text-white">
                Registrierung fuer erste Checks, Projekte und Kaufpfade
              </h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
                Ihr Konto verknuepft neue Checks mit Projekten, Analyse-History, Paketwahl und spaeteren Reports.
                So bleibt fachlich nachvollziehbar, was Self-Serve ist und wo Service- oder Pilotpfade beginnen.
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
              <p className="mt-2 text-xs leading-5 text-text-muted">Nach Registrierung: {intentProfile.nextStep}</p>
              {checkoutPlan && offerIdForCheckoutPlan(checkoutPlan) ? (
                <p className="mt-2 text-xs leading-5 text-brand-cyan">
                  Gewaehltes Paket: {checkoutPlan}. Nach der Registrierung startet Stripe Checkout automatisch.
                </p>
              ) : null}
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Klarer Einstieg</p>
                <p className="mt-2 text-sm text-white">3 Free Checks fuer den ersten Produktfit und den Weg zu den passenden Paketen.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Kontobezogene History</p>
                <p className="mt-2 text-sm text-white">Analysen, Reportscope und Revisionen bleiben nutzerbezogen verstaendlich.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Servicegrenzen sichtbar</p>
                <p className="mt-2 text-sm text-white">Professional, Express und VNB Pilot bleiben bewusst getrennte Produktpfade.</p>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-white">
                  <UserRound className="h-4 w-4 text-brand-cyan" />
                  Konto zuerst, Routing danach
                </p>
                <p className="mt-2 text-sm leading-6 text-text-muted">
                  Nach der Registrierung geht es direkt weiter zu{" "}
                  <span className="font-medium text-white">
                    {nextTarget.includes("checkout=1")
                      ? "Stripe Checkout"
                      : nextTarget === "/settings"
                        ? "Tarif & Analyse-History"
                        : nextTarget === "/onboarding"
                          ? "der Einfuehrung"
                          : "Ihren Projekten"}
                  </span>
                  .
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-white">
                  <CheckCircle2 className="h-4 w-4 text-brand-orange" />
                  MVP-tauglicher Einstieg
                </p>
                <p className="mt-2 text-sm leading-6 text-text-muted">
                  Wer noch nicht registrieren moechte, kann trotzdem jederzeit den aktiven Projektierer-Einstieg oder den
                  Anfragepfad nutzen.
                </p>
              </div>
            </div>
          </section>

          <section className={cardClass}>
            <h2 className="text-2xl font-semibold text-white">Registrierung</h2>
            <p className="mt-2 text-sm leading-6 text-text-muted">
              Legen Sie ein Konto fuer Projekte, Analyse-History und den passenden Upgrade- oder Anfragepfad an.
            </p>

            <form onSubmit={onSubmit} className="mt-6 space-y-4">
              <div className="space-y-2">
                <Label htmlFor="register-name" className="text-white">
                  Name oder Teamname
                </Label>
                <Input
                  id="register-name"
                  autoComplete="name"
                  className={fieldClass}
                  placeholder="z.B. Projektentwicklung Nord"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="register-email" className="text-white">
                  E-Mail
                </Label>
                <Input
                  id="register-email"
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
                  <Label htmlFor="register-password" className="text-white">
                    Passwort
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
                  id="register-password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="new-password"
                  className={fieldClass}
                  placeholder="Mindestens 12 Zeichen, komplex"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="register-role" className="text-white">
                  Rolle
                </Label>
                <select id="register-role" className={selectClass} value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="projektierer">Projektierer / EPC</option>
                  <option value="netzbetreiber">Netzbetreiber</option>
                  <option value="endkunde">Sonstige / Endkunde</option>
                </select>
                <p className="text-xs leading-5 text-text-muted">
                  Die Rolle dient der fachlichen Einordnung Ihrer Standardansicht und ersetzt keine finale Produkt- oder
                  Paketwahl.
                </p>
              </div>

              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                <p className="text-sm font-medium text-white">Pruefung</p>
                <div className="mt-3 grid gap-2 sm:grid-cols-3">
                  {formChecks.map((check) => (
                    <div
                      key={check.label}
                      className={`rounded-xl border px-3 py-2 text-sm ${
                        check.ok
                          ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
                          : "border-white/10 bg-black/10 text-text-muted"
                      }`}
                    >
                      {check.label}
                    </div>
                  ))}
                </div>
              </div>

              {error ? (
                <div className="space-y-2">
                  <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                    {error}
                  </div>
                  {isAuthInfrastructureError(error) && (
                    <p className="text-xs text-text-dim">
                      Diagnose:{" "}
                      <Link href="/api-test" className="text-brand-cyan underline">
                        /api-test
                      </Link>
                      . Vercel: BACKEND_URL=https://gridcheck-production.up.railway.app — siehe docs/LAUNCH.md.
                    </p>
                  )}
                </div>
              ) : null}

              <Button
                type="submit"
                disabled={isSubmitting}
                className="h-11 w-full rounded-xl bg-brand-orange text-white hover:bg-brand-orangeHover"
              >
                {isSubmitting
                  ? checkoutPlan
                    ? "Konto wird angelegt, Checkout startet..."
                    : "Konto wird angelegt..."
                  : checkoutPlan
                    ? "Konto anlegen und fortfahren"
                    : "Konto anlegen"}
              </Button>
            </form>

            <div className="mt-5 rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-text-muted">
              Nach der Registrierung werden Sie automatisch angemeldet und weitergeleitet zu{" "}
              <span className="font-medium text-white">
                {nextTarget.includes("checkout=1")
                  ? "Stripe Checkout"
                  : nextTarget === "/settings"
                    ? "Tarif & Analyse-History"
                    : nextTarget === "/onboarding"
                      ? "der Einfuehrung"
                      : "Ihren Projekten"}
              </span>
              . Den direkten Frontend-Einstieg finden Sie ausserdem im{" "}
              <Link className="font-medium text-brand-cyan" href="/projektierer">
                Projektierer-Modul
              </Link>
              .
            </div>

            <div className="mt-5 flex flex-col gap-3 sm:flex-row">
              <Button asChild className="h-11 rounded-xl bg-brand-cyan text-slate-950 hover:bg-brand-cyan/90">
                <Link href={loginHref}>
                  Zum Login
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" className="h-11 rounded-xl border-white/15 bg-transparent text-white hover:bg-white/5">
                <Link href={`/contact?intent=${encodeURIComponent(intent)}`}>Erst Produktpfad klaeren</Link>
              </Button>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

export default function RegisterPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-bg text-white" />}>
      <RegisterPageContent />
    </Suspense>
  );
}
