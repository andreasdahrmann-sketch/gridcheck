"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { Download, ShieldAlert, ShieldCheck, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { logout } from "@/lib/api/auth";
import { getCsrfTokenFromCookie } from "@/lib/api/csrf";
import { bearerAuthHeaders } from "@/lib/api/session";

type Notice = { tone: "success" | "error"; text: string } | null;

const cardClass =
  "rounded-[24px] border border-border/70 bg-bg-card/80 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";
const fieldClass =
  "h-11 rounded-xl border-border/70 bg-white/5 px-3 text-white placeholder:text-text-dim focus-visible:border-brand-cyan/70 focus-visible:ring-brand-cyan/20";

const EXPORT_ENDPOINT = "/api/backend/api/v1/users/me/data-export";
const DELETE_ENDPOINT = "/api/backend/api/v1/users/me/delete-account";

function filenameFromContentDisposition(header: string | null, fallback: string): string {
  if (!header) return fallback;
  const match = header.match(/filename\s*=\s*"?([^"]+)"?/i);
  return match?.[1] ?? fallback;
}

export default function PrivacySettingsPage() {
  const [exportNotice, setExportNotice] = useState<Notice>(null);
  const [exportPending, setExportPending] = useState(false);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState("");
  const [acknowledged, setAcknowledged] = useState(false);
  const [deleteNotice, setDeleteNotice] = useState<Notice>(null);
  const [deletePending, setDeletePending] = useState(false);

  async function handleExport() {
    if (exportPending) return;
    setExportPending(true);
    setExportNotice(null);
    try {
      const csrf = getCsrfTokenFromCookie();
      const res = await fetch(EXPORT_ENDPOINT, {
        method: "POST",
        credentials: "include",
        headers: {
          ...(csrf ? { "X-CSRF-Token": csrf } : {}),
          ...bearerAuthHeaders(),
        },
      });
      if (res.status === 429) {
        setExportNotice({
          tone: "error",
          text: "Datenexport bereits angefordert. Pro Konto ist nur ein Export je 24 Stunden vorgesehen.",
        });
        return;
      }
      if (!res.ok) {
        setExportNotice({ tone: "error", text: `Export fehlgeschlagen (HTTP ${res.status}).` });
        return;
      }
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const fallback = `gridcheck_export_${new Date().toISOString().replace(/[:.]/g, "-")}.zip`;
      const filename = filenameFromContentDisposition(res.headers.get("content-disposition"), fallback);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = filename;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      setExportNotice({ tone: "success", text: "Datenexport heruntergeladen." });
    } catch {
      setExportNotice({ tone: "error", text: "Netzwerkfehler beim Datenexport." });
    } finally {
      setExportPending(false);
    }
  }

  async function handleDelete(event: FormEvent) {
    event.preventDefault();
    if (deletePending || !acknowledged || confirmPassword.length === 0) return;
    setDeletePending(true);
    setDeleteNotice(null);
    try {
      const csrf = getCsrfTokenFromCookie();
      const res = await fetch(DELETE_ENDPOINT, {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrf ? { "X-CSRF-Token": csrf } : {}),
          ...bearerAuthHeaders(),
        },
        body: JSON.stringify({ confirm_password: confirmPassword }),
      });
      if (res.status === 204) {
        try {
          await logout();
        } catch {
          // Auch wenn Logout fehlschlaegt: Server-Token ist bereits invalidiert.
        }
        window.location.href = "/";
        return;
      }
      if (res.status === 401) {
        setDeleteNotice({ tone: "error", text: "Passwort-Bestaetigung fehlgeschlagen." });
        return;
      }
      if (res.status === 429) {
        setDeleteNotice({ tone: "error", text: "Zu viele Loeschversuche. Bitte spaeter erneut." });
        return;
      }
      setDeleteNotice({ tone: "error", text: `Loeschung fehlgeschlagen (HTTP ${res.status}).` });
    } catch {
      setDeleteNotice({ tone: "error", text: "Netzwerkfehler bei der Konto-Loeschung." });
    } finally {
      setDeletePending(false);
    }
  }

  return (
    <div className="mx-auto max-w-4xl">
      <div className="flex flex-col gap-4 border-b border-border/70 pb-6">
        <div>
          <p className="text-sm font-medium uppercase tracking-[0.24em] text-brand-cyan">DSGVO Self-Service</p>
          <h1 className="mt-2 text-3xl font-semibold text-white">Datenschutz &amp; Konto</h1>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
            Auskunfts- und Loeschrechte nach Art. 15, 17 und 20 DSGVO. Details zum Hintergrund finden Sie in
            der{" "}
            <Link href="/datenschutz" className="text-brand-cyan hover:underline">
              Datenschutzerklaerung
            </Link>
            .
          </p>
        </div>
        <Link
          href="/settings"
          className="text-xs text-text-dim hover:text-text-muted"
        >
          &larr; Zurueck zu Einstellungen
        </Link>
      </div>

      <div className="mt-6 grid gap-6">
        <Card className={cardClass}>
          <CardHeader className="gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-brand-cyan">
                <Download className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-white">Datenexport anfordern (Art. 15 / 20 DSGVO)</CardTitle>
                <CardDescription className="text-text-muted">
                  ZIP-Archiv mit Konto-, Projekt-, Report-, Audit- und Billing-Daten.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm leading-6 text-text-muted">
              Der Export enthaelt alle gespeicherten personenbezogenen Daten zu Ihrem Konto, einschliesslich
              soft-geloeschter Projekte. Maximal <strong className="text-white">1 Export pro 24 Stunden</strong>{" "}
              pro Konto. Der Vorgang wird im Audit-Trail revisionssicher protokolliert.
            </p>
            {exportNotice ? (
              <div
                className={`rounded-2xl border px-4 py-3 text-sm ${
                  exportNotice.tone === "success"
                    ? "border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan"
                    : "border-red-500/30 bg-red-500/10 text-red-300"
                }`}
              >
                {exportNotice.text}
              </div>
            ) : null}
            <Button
              type="button"
              onClick={handleExport}
              disabled={exportPending}
              className="h-11 rounded-xl bg-brand-cyan px-5 text-black hover:bg-brand-cyan/90"
            >
              {exportPending ? "Erzeuge Export..." : "Datenexport herunterladen"}
            </Button>
          </CardContent>
        </Card>

        <Card className={`${cardClass} border-red-500/30`}>
          <CardHeader className="gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-red-500/30 bg-red-500/10 text-red-300">
                <ShieldAlert className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-white">Konto endgueltig loeschen (Art. 17 DSGVO)</CardTitle>
                <CardDescription className="text-text-muted">
                  Soft-Delete mit Anonymisierung. Aus revisionssicheren Gruenden kein Hard-Delete.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-sm leading-6 text-text-muted">
              <p className="font-medium text-white">Was wird geloescht / anonymisiert:</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li>Login-Daten (E-Mail, Passwort, Name) werden anonymisiert; Konto wird deaktiviert.</li>
                <li>Alle eigenen Projekte werden soft-geloescht.</li>
                <li>Aktive Sessions und Tokens werden invalidiert.</li>
              </ul>
              <p className="mt-3 font-medium text-white">Was bleibt aus rechtlichen Gruenden bestehen:</p>
              <ul className="mt-2 list-disc space-y-1 pl-5">
                <li>
                  Audit-/Revisions-Hash-Kette (vertragliche und gesetzliche Nachweisbarkeit, siehe Rule 05
                  Revisionssicherheit).
                </li>
                <li>
                  Abrechnungs- und Buchhaltungsdaten gemaess <strong className="text-white">§ 257 HGB / § 147 AO</strong>{" "}
                  fuer 6 bzw. 10 Jahre.
                </li>
              </ul>
              <p className="mt-3 text-xs text-text-dim">
                Eine erneute Registrierung mit derselben E-Mail-Adresse ist nach der Loeschung gesperrt.
              </p>
            </div>

            {!deleteOpen ? (
              <Button
                type="button"
                variant="outline"
                onClick={() => setDeleteOpen(true)}
                className="h-11 rounded-xl border-red-500/40 bg-transparent text-red-200 hover:bg-red-500/10"
              >
                Konto endgueltig loeschen
              </Button>
            ) : (
              <form onSubmit={handleDelete} className="space-y-4">
                <div className="flex items-start gap-2 rounded-2xl border border-red-500/30 bg-red-500/5 px-4 py-3 text-sm text-red-200">
                  <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                  <p>
                    Diese Aktion kann <strong>nicht</strong> rueckgaengig gemacht werden. Bitte zuvor einen
                    Datenexport herunterladen.
                  </p>
                </div>
                <div className="space-y-2">
                  <Label htmlFor="confirm-password" className="text-white">
                    Aktuelles Passwort zur Bestaetigung
                  </Label>
                  <Input
                    id="confirm-password"
                    type="password"
                    value={confirmPassword}
                    onChange={(event) => setConfirmPassword(event.target.value)}
                    className={fieldClass}
                    autoComplete="current-password"
                    placeholder="Aktuelles Passwort"
                  />
                </div>
                <label className="flex items-start gap-3 text-sm text-text-muted" htmlFor="ack-delete">
                  <input
                    id="ack-delete"
                    type="checkbox"
                    className="mt-1 h-4 w-4 rounded border-white/30 bg-white/10 text-brand-cyan focus:ring-brand-cyan"
                    checked={acknowledged}
                    onChange={(event) => setAcknowledged(event.target.checked)}
                  />
                  <span>
                    Ich verstehe, dass die Loeschung als Soft-Delete erfolgt und Audit- sowie
                    Abrechnungs-/Buchhaltungsdaten aus gesetzlichen Gruenden weiterhin sperrgespeichert bleiben.
                  </span>
                </label>
                {deleteNotice ? (
                  <div
                    className={`rounded-2xl border px-4 py-3 text-sm ${
                      deleteNotice.tone === "success"
                        ? "border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan"
                        : "border-red-500/30 bg-red-500/10 text-red-300"
                    }`}
                  >
                    {deleteNotice.text}
                  </div>
                ) : null}
                <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-end">
                  <Button
                    type="button"
                    variant="ghost"
                    onClick={() => {
                      setDeleteOpen(false);
                      setConfirmPassword("");
                      setAcknowledged(false);
                      setDeleteNotice(null);
                    }}
                    className="h-11 rounded-xl px-5 text-white hover:bg-white/10"
                  >
                    Abbrechen
                  </Button>
                  <Button
                    type="submit"
                    disabled={!acknowledged || confirmPassword.length === 0 || deletePending}
                    className="h-11 rounded-xl bg-red-600 px-5 text-white hover:bg-red-600/90 disabled:opacity-60"
                  >
                    {deletePending ? "Loeschung laeuft..." : "Konto endgueltig loeschen"}
                  </Button>
                </div>
              </form>
            )}
          </CardContent>
        </Card>

        <Card className={cardClass}>
          <CardHeader className="gap-3">
            <div className="flex items-center gap-3">
              <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-brand-mint">
                <ShieldCheck className="h-5 w-5" />
              </div>
              <div>
                <CardTitle className="text-white">Weitere Betroffenenrechte</CardTitle>
                <CardDescription className="text-text-muted">
                  Berichtigung, Einschraenkung, Widerspruch, Widerruf erteilter Einwilligungen.
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <p className="text-sm leading-6 text-text-muted">
              Anfragen zu Art. 16, 18, 21 und 7 Abs. 3 DSGVO richten Sie bitte an die in der{" "}
              <Link href="/datenschutz" className="text-brand-cyan hover:underline">
                Datenschutzerklaerung
              </Link>{" "}
              genannte Kontaktadresse.
            </p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
