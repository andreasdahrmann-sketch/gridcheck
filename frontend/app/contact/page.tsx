"use client";

import { FormEvent, Suspense, useState } from "react";
import Link from "next/link";
import { ArrowRight, CheckCircle2, Mail, MessageSquareText } from "lucide-react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { submitContact } from "@/lib/api/contact";
import { getPurchaseIntentProfile, listPurchaseIntentProfiles, normalizePurchaseIntent, type PurchaseIntent } from "@/lib/purchase-intents";

const cardClass = "rounded-[28px] border border-white/10 bg-bg-card/80 p-6 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";
const fieldClass =
  "h-11 rounded-xl border-border/70 bg-white/5 px-3 text-white placeholder:text-text-dim focus-visible:border-brand-cyan/70 focus-visible:ring-brand-cyan/20";
const textareaClass =
  "min-h-[180px] w-full rounded-xl border border-border/70 bg-white/5 px-3 py-3 text-sm text-white placeholder:text-text-dim outline-none transition focus:border-brand-cyan/70 focus:ring-2 focus:ring-brand-cyan/20";

type Notice =
  | {
      tone: "success" | "error";
      text: string;
    }
  | null;

function ContactPageContent() {
  const searchParams = useSearchParams();
  const initialIntent = normalizePurchaseIntent(searchParams.get("intent"));
  const initialProfile = getPurchaseIntentProfile(initialIntent);
  const [selectedIntent, setSelectedIntent] = useState<PurchaseIntent>(initialIntent);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [subject, setSubject] = useState(initialProfile.subject);
  const [message, setMessage] = useState(initialProfile.suggestedMessage);
  const [result, setResult] = useState<Notice>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const selectedProfile = getPurchaseIntentProfile(selectedIntent);
  const loginHref = `/login?intent=${encodeURIComponent(selectedIntent)}&next=${encodeURIComponent(selectedIntent === "upgrade" || selectedIntent === "pro" ? "/settings" : "/projects")}`;
  const selfServeHref = selectedIntent === "upgrade" || selectedIntent === "pro" ? "/settings" : "/projektierer";
  const selfServeLabel = selectedIntent === "upgrade" || selectedIntent === "pro" ? "Tarife & Verlauf" : "Direkt zum Projektierer-Modul";

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setResult(null);

    if (!name.trim() || !email.trim() || !subject.trim() || !message.trim()) {
      setResult({ tone: "error", text: "Bitte alle Pflichtfelder ausfuellen." });
      return;
    }

    setIsSubmitting(true);
    try {
      await submitContact({ name: name.trim(), email: email.trim(), subject: subject.trim(), message: message.trim() });
      setResult({ tone: "success", text: "Nachricht wurde gesendet." });
      setMessage("");
    } catch (err) {
      setResult({ tone: "error", text: err instanceof Error ? err.message : "Senden fehlgeschlagen." });
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-10">
        <div className="grid gap-6 xl:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)]">
          <section className="space-y-6">
            <div className="rounded-[28px] border border-white/10 bg-white/5 p-6">
              <div className="inline-flex rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-brand-cyan">
                Kontakt & Anfragepfade
              </div>
              <h1 className="mt-4 text-3xl font-semibold text-white">Den richtigen Produktpfad fuer Ihr Vorhaben abstimmen</h1>
              <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
                Nutzen Sie diese Seite fuer Professional, Express, VNB Pilot oder allgemeine Produktfragen. Self-Serve,
                laufende SaaS-Nutzung und betreute Servicepfade bleiben bewusst getrennt, damit Scope und naechste
                Schritte klar bleiben.
              </p>
            </div>

            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {listPurchaseIntentProfiles().map((profile) => {
                const isActive = selectedIntent === profile.id;
                return (
                  <button
                    key={profile.id}
                    type="button"
                    onClick={() => {
                      setSelectedIntent(profile.id);
                      setSubject(profile.subject);
                      setMessage(profile.suggestedMessage);
                      setResult(null);
                    }}
                    className={`rounded-2xl border p-4 text-left transition ${
                      isActive
                        ? "border-brand-cyan/40 bg-brand-cyan/10"
                        : "border-white/10 bg-white/5 hover:border-brand-cyan/20"
                    }`}
                  >
                    <div className="flex items-center gap-2">
                      <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-white">
                        {profile.badge}
                      </span>
                      <span className="text-sm font-semibold text-white">{profile.shortLabel}</span>
                    </div>
                    <p className="mt-3 text-sm leading-6 text-white/90">{profile.summary}</p>
                    <p className="mt-2 text-xs leading-5 text-text-muted">{profile.audience}</p>
                  </button>
                );
              })}
            </div>

            <div className="grid gap-3 md:grid-cols-3">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Self-Serve</p>
                <p className="mt-2 text-sm text-white">Free, Basic, Premium und Pro decken den eigenstaendigen Analysepfad ab.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Professional</p>
                <p className="mt-2 text-sm text-white">Professional ist betreute Anschlussstrategie mit sichtbarem Follow-up.</p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="text-xs uppercase tracking-[0.18em] text-text-dim">Express / VNB Pilot</p>
                <p className="mt-2 text-sm text-white">Express ist ein Zeit-Zusatz; VNB Pilot bleibt ein abgestimmter Pilotpfad.</p>
              </div>
            </div>

            <div className="grid gap-3 md:grid-cols-2">
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-white">
                  <Mail className="h-4 w-4 text-brand-cyan" />
                  Klarer Anfragekontext
                </p>
                <p className="mt-2 text-sm leading-6 text-text-muted">
                  Betreff und Nachricht werden auf den gewaehlten Produktpfad vorbefuellt und bleiben manuell
                  anpassbar.
                </p>
              </div>
              <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                <p className="flex items-center gap-2 text-sm font-semibold text-white">
                  <CheckCircle2 className="h-4 w-4 text-brand-orange" />
                  Routing bleibt offen
                </p>
                <p className="mt-2 text-sm leading-6 text-text-muted">
                  Selbst nach einer Anfrage bleiben Self-Serve-Check, Login und Tarifseite als alternative Wege direkt
                  erreichbar.
                </p>
              </div>
            </div>
          </section>

          <section className={`space-y-5 ${cardClass}`}>
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <span className="rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-brand-cyan">
                  {selectedProfile.badge}
                </span>
                <span className="text-sm font-semibold text-white">{selectedProfile.label}</span>
              </div>
              <p className="mt-3 text-sm leading-6 text-text-muted">{selectedProfile.summary}</p>
              <p className="mt-2 text-xs leading-5 text-text-dim">Naechster Schritt: {selectedProfile.nextStep}</p>
            </div>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <p className="flex items-center gap-2 text-sm font-medium text-white">
                <MessageSquareText className="h-4 w-4 text-brand-cyan" />
                Was in die Anfrage gehoert
              </p>
              <ul className="mt-3 space-y-2 text-sm leading-6 text-text-muted">
                <li>Projektart, Leistung, Standort oder Bundesland.</li>
                <li>Warum Sie Self-Serve, Pro, Professional, Express oder VNB Pilot pruefen.</li>
                <li>Wichtige Frist, Entscheidungsdatum oder internen Stakeholder-Kontext.</li>
              </ul>
            </div>

            <form onSubmit={onSubmit} className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="contact-name" className="text-white">
                  Name
                </Label>
                <Input
                  id="contact-name"
                  autoComplete="name"
                  className={fieldClass}
                  placeholder="Ihr Name oder Team"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="contact-email" className="text-white">
                  E-Mail
                </Label>
                <Input
                  id="contact-email"
                  type="email"
                  autoComplete="email"
                  className={fieldClass}
                  placeholder="name@firma.de"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="contact-subject" className="text-white">
                  Betreff
                </Label>
                <Input
                  id="contact-subject"
                  className={fieldClass}
                  placeholder="Worum geht es?"
                  value={subject}
                  onChange={(e) => setSubject(e.target.value)}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="contact-message" className="text-white">
                  Nachricht
                </Label>
                <textarea
                  id="contact-message"
                  className={textareaClass}
                  rows={8}
                  placeholder="Kurz Projekt, Zeitdruck, Zielbild und gewuenschten Produktpfad beschreiben"
                  value={message}
                  onChange={(e) => setMessage(e.target.value)}
                  required
                />
              </div>

              {result ? (
                <div
                  className={`rounded-2xl border px-4 py-3 text-sm ${
                    result.tone === "success"
                      ? "border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan"
                      : "border-red-500/30 bg-red-500/10 text-red-300"
                  }`}
                >
                  {result.text}
                </div>
              ) : null}

              <Button
                type="submit"
                disabled={isSubmitting}
                className="h-11 w-full rounded-xl bg-brand-orange text-white hover:bg-brand-orangeHover"
              >
                {isSubmitting ? "Sendet Anfrage..." : "Anfrage senden"}
              </Button>
            </form>

            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-text-muted">
              Wenn Sie zuerst selbst pruefen moechten:{" "}
              <Link href={selfServeHref} className="font-medium text-brand-cyan">
                {selfServeLabel}
              </Link>{" "}
              oder{" "}
              <Link href={loginHref} className="font-medium text-brand-cyan">
                direkt einloggen
              </Link>
              .
            </div>

            <div className="flex flex-col gap-3 sm:flex-row">
              <Button asChild className="h-11 rounded-xl bg-brand-cyan text-slate-950 hover:bg-brand-cyan/90">
                <Link href={selfServeHref}>
                  {selfServeLabel}
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Link>
              </Button>
              <Button asChild variant="outline" className="h-11 rounded-xl border-white/15 bg-transparent text-white hover:bg-white/5">
                <Link href={loginHref}>Login mit Zielrouting</Link>
              </Button>
            </div>
          </section>
        </div>
      </div>
    </main>
  );
}

export default function ContactPage() {
  return (
    <Suspense fallback={<main className="min-h-screen bg-bg text-white" />}>
      <ContactPageContent />
    </Suspense>
  );
}
