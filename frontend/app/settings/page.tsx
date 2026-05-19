"use client";

import { FormEvent, Suspense, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import {
  Laptop2,
  LockKeyhole,
  LogOut,
  Mail,
  ShieldCheck,
  UserRound,
  Eye,
  EyeOff,
} from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import BillingAndHistoryPanel from "@/components/settings/BillingAndHistoryPanel";
import { logout } from "@/lib/api/auth";
import { getCsrfTokenFromCookie } from "@/lib/api/csrf";
import { bearerAuthHeaders } from "@/lib/api/session";
import {
  DEFAULT_USER_PREFERENCES,
  readUserPreferences,
  resetUserPreferences,
  saveUserPreferences,
  type UserPreferences,
} from "@/lib/user-preferences";
import { formSelectClass as selectClass } from "@/lib/form-classes";

type Me = { id: number; email: string; role: string; full_name?: string | null };

type Notice =
  | {
      tone: "success" | "error";
      text: string;
    }
  | null;

const cardClass = "rounded-[24px] border border-border/70 bg-bg-card/80 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";
const fieldClass =
  "h-11 rounded-xl border-border/70 bg-white/5 px-3 text-white placeholder:text-text-dim focus-visible:border-brand-cyan/70 focus-visible:ring-brand-cyan/20";

function PreferenceRow({
  title,
  description,
  checked,
  onCheckedChange,
}: {
  title: string;
  description: string;
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-4 rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium text-white">{title}</p>
        <p className="mt-1 text-sm leading-6 text-text-muted">{description}</p>
      </div>
      <Switch checked={checked} onCheckedChange={onCheckedChange} aria-label={title} />
    </div>
  );
}

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPasswords, setShowPasswords] = useState(false);
  const [preferences, setPreferences] = useState<UserPreferences>(DEFAULT_USER_PREFERENCES);
  const [savedPreferences, setSavedPreferences] = useState<UserPreferences>(DEFAULT_USER_PREFERENCES);
  const [preferencesReady, setPreferencesReady] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [isLoggingOut, setIsLoggingOut] = useState(false);

  const meQuery = useQuery<Me>({
    queryKey: ["me"],
    queryFn: async () => {
      const res = await fetch("/api/backend/api/v1/users/me", {
        credentials: "include",
        cache: "no-store",
        headers: { ...bearerAuthHeaders() },
      });
      if (!res.ok) {
        throw new Error("not-authorized");
      }
      return res.json();
    },
  });

  useEffect(() => {
    const nextPreferences = readUserPreferences();
    setPreferences(nextPreferences);
    setSavedPreferences(nextPreferences);
    setPreferencesReady(true);
  }, []);

  useEffect(() => {
    if (meQuery.data) {
      setFullName(meQuery.data.full_name ?? "");
    }
  }, [meQuery.data]);

  useEffect(() => {
    if (meQuery.isError) {
      window.location.href = "/login";
    }
  }, [meQuery.isError]);

  const profileMutation = useMutation({
    mutationFn: async (nextFullName: string) => {
      const csrf = getCsrfTokenFromCookie();
      const res = await fetch("/api/backend/api/v1/users/me", {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
        body: JSON.stringify({ full_name: nextFullName }),
      });
      if (!res.ok) {
        throw new Error("save-failed");
      }
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
      setNotice({ tone: "success", text: "Profil aktualisiert." });
    },
    onError: () => {
      setNotice({ tone: "error", text: "Profil konnte nicht gespeichert werden." });
    },
  });

  const passwordMutation = useMutation({
    mutationFn: async (payload: { currentPassword: string; newPassword: string }) => {
      const csrf = getCsrfTokenFromCookie();
      const res = await fetch("/api/backend/api/v1/users/me/password", {
        method: "PATCH",
        credentials: "include",
        headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRF-Token": csrf } : {}) },
        body: JSON.stringify({ current_password: payload.currentPassword, new_password: payload.newPassword }),
      });
      if (!res.ok) {
        throw new Error("password-failed");
      }
      return res.json();
    },
    onSuccess: () => {
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
      setNotice({ tone: "success", text: "Passwort geaendert." });
    },
    onError: () => {
      setNotice({ tone: "error", text: "Passwort konnte nicht geaendert werden." });
    },
  });

  const trimmedFullName = fullName.trim();
  const originalFullName = (meQuery.data?.full_name ?? "").trim();
  const profileDirty = trimmedFullName !== originalFullName;
  const preferencesDirty = JSON.stringify(preferences) !== JSON.stringify(savedPreferences);

  const passwordChecks = useMemo(
    () => [
      { label: "Aktuelles Passwort eingegeben", ok: currentPassword.trim().length > 0 },
      { label: "Mindestens 8 Zeichen", ok: newPassword.length >= 8 },
      { label: "Neues Passwort bestaetigt", ok: newPassword.length > 0 && newPassword === confirmPassword },
      { label: "Unterscheidet sich vom aktuellen", ok: !!newPassword && currentPassword !== newPassword },
    ],
    [confirmPassword, currentPassword, newPassword]
  );

  const canSavePassword = passwordChecks.every((check) => check.ok) && !passwordMutation.isPending;

  async function onSaveProfile(event: FormEvent) {
    event.preventDefault();
    if (!profileDirty || profileMutation.isPending) {
      return;
    }

    await profileMutation.mutateAsync(trimmedFullName);
  }

  function onSavePreferences(event: FormEvent) {
    event.preventDefault();
    const next = saveUserPreferences(preferences);
    setPreferences(next);
    setSavedPreferences(next);
    setNotice({ tone: "success", text: "Lokale Arbeits- und Darstellungsoptionen gespeichert." });
  }

  async function onChangePassword(event: FormEvent) {
    event.preventDefault();
    if (!canSavePassword) {
      return;
    }

    await passwordMutation.mutateAsync({ currentPassword, newPassword });
  }

  function onResetPreferences() {
    const next = resetUserPreferences();
    setPreferences(next);
    setSavedPreferences(next);
    setNotice({ tone: "success", text: "Lokale Einstellungen wurden auf Standardwerte gesetzt." });
  }

  async function onLogout() {
    if (isLoggingOut) {
      return;
    }

    setIsLoggingOut(true);
    try {
      await logout();
      window.location.href = "/login";
    } catch {
      setNotice({ tone: "error", text: "Abmeldung fehlgeschlagen. Bitte erneut versuchen." });
      setIsLoggingOut(false);
    }
  }

  return (
    <div className="mx-auto max-w-6xl">
        <div className="flex flex-col gap-4 border-b border-border/70 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-brand-cyan">Account & Workflow</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">Einstellungen</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
              Konto, Passwort und die wichtigsten Arbeitsvorgaben fuer Check, Dashboard und Projektlisten.
            </p>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs sm:w-[320px]">
            <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
              <div className="text-text-dim">Profilstatus</div>
              <div className="mt-1 font-semibold text-white">{profileDirty ? "Ungespeichert" : "Synchron"}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 px-3 py-3">
              <div className="text-text-dim">Lokale Voreinstellungen</div>
              <div className="mt-1 font-semibold text-white">{preferencesDirty ? "Geaendert" : "Aktiv"}</div>
            </div>
          </div>
        </div>

        {notice ? (
          <div
            className={`mt-6 rounded-2xl border px-4 py-3 text-sm ${
              notice.tone === "success"
                ? "border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan"
                : "border-red-500/30 bg-red-500/10 text-red-300"
            }`}
          >
            {notice.text}
          </div>
        ) : null}

        {meQuery.isLoading ? (
          <div className="mt-6 rounded-2xl border border-border bg-bg-elev px-4 py-4 text-sm text-text-muted">
            Lade Profil...
          </div>
        ) : null}

        {meQuery.isError ? (
          <div className="mt-6 rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-4 text-sm text-red-300">
            Profil konnte nicht geladen werden.
          </div>
        ) : null}

        <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.45fr)_minmax(320px,0.9fr)]">
          <div className="space-y-6">
            <Suspense fallback={<div className={`${cardClass} p-6 text-sm text-text-muted`}>Lade Abrechnung...</div>}>
              <BillingAndHistoryPanel cardClass={cardClass} isAdmin={meQuery.data?.role === "admin"} />
            </Suspense>

            {meQuery.data?.role === "admin" ? (
              <Card className={cardClass}>
                <CardHeader className="gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-brand-cyan">
                      <ShieldCheck className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle className="text-white">Interner OPS-Workflow</CardTitle>
                      <CardDescription className="text-text-muted">
                        Admin-Queue fuer Professional- und Express-Follow-ups mit Claim-, Bearbeitungs- und Abschlusslogik.
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
                  <p className="text-sm leading-6 text-text-muted">
                    Nutzen Sie die dedizierte OPS-Seite fuer Zuweisung, Statuswechsel und interne Bearbeitungshinweise.
                  </p>
                  <Link
                    href="/ops"
                    className="inline-flex h-11 items-center justify-center rounded-xl bg-brand-cyan px-5 text-sm font-semibold text-black transition hover:bg-brand-cyan/90"
                  >
                    OPS-Queue oeffnen
                  </Link>
                </CardContent>
              </Card>
            ) : null}

            <Card className={cardClass}>
              <CardHeader className="gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-brand-orange">
                    <UserRound className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-white">Profil</CardTitle>
                    <CardDescription className="text-text-muted">
                      Oeffentlicher Anzeigename und Kontodaten fuer den eingeloggten Nutzer.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={onSaveProfile} className="space-y-5">
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="settings-email" className="text-white">
                        E-Mail
                      </Label>
                      <div className="relative">
                        <Mail className="pointer-events-none absolute left-3 top-3.5 h-4 w-4 text-text-dim" />
                        <Input
                          id="settings-email"
                          readOnly
                          value={meQuery.data?.email ?? ""}
                          className={`${fieldClass} pl-9 text-text-muted`}
                        />
                      </div>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="settings-role" className="text-white">
                        Rolle
                      </Label>
                      <Input
                        id="settings-role"
                        readOnly
                        value={meQuery.data?.role ?? ""}
                        className={`${fieldClass} text-text-muted`}
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="settings-full-name" className="text-white">
                      Anzeigename
                    </Label>
                    <Input
                      id="settings-full-name"
                      placeholder="Ihr Name oder Teamname"
                      value={fullName}
                      onChange={(event) => setFullName(event.target.value)}
                      className={fieldClass}
                    />
                    <p className="text-sm text-text-muted">
                      Wird fuer persoenliche Bezeichnungen und kuenftige Freigaben verwendet.
                    </p>
                  </div>

                  <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
                    <p className="text-sm text-text-muted">
                      {profileDirty ? "Es gibt ungespeicherte Profil-Aenderungen." : "Profil ist auf dem aktuellen Stand."}
                    </p>
                    <Button
                      type="submit"
                      disabled={!profileDirty || profileMutation.isPending}
                      className="h-11 rounded-xl bg-brand-orange px-5 text-white hover:bg-brand-orangeHover"
                    >
                      {profileMutation.isPending ? "Speichert..." : "Profil speichern"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            <Card className={cardClass}>
              <CardHeader className="gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-brand-cyan">
                    <Laptop2 className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-white">Arbeitsbereich</CardTitle>
                    <CardDescription className="text-text-muted">
                      Lokale Vorgaben fuer Startansicht, mobile Nutzung und Listendarstellung.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={onSavePreferences} className="space-y-5">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="default-landing-tab" className="text-white">
                        Standard-Startansicht
                      </Label>
                      <select
                        id="default-landing-tab"
                        className={selectClass}
                        value={preferences.defaultLandingTab}
                        onChange={(event) =>
                          setPreferences((current) => ({
                            ...current,
                            defaultLandingTab: event.target.value as UserPreferences["defaultLandingTab"],
                          }))
                        }
                      >
                        <option value="check" className="bg-bg text-white">
                          Netzanschluss-Check
                        </option>
                        <option value="dashboard" className="bg-bg text-white">
                          Netzbetreiber-Dashboard
                        </option>
                      </select>
                    </div>

                    <div className="space-y-2">
                      <Label htmlFor="default-customer-type" className="text-white">
                        Standard-Kundentyp fuer neue Checks
                      </Label>
                      <select
                        id="default-customer-type"
                        className={selectClass}
                        value={preferences.defaultCustomerType}
                        onChange={(event) =>
                          setPreferences((current) => ({
                            ...current,
                            defaultCustomerType: event.target.value as UserPreferences["defaultCustomerType"],
                          }))
                        }
                      >
                        <option value="" className="bg-bg text-white">
                          Keine Vorauswahl
                        </option>
                        <option value="projektierer" className="bg-bg text-white">
                          Projektierer / EPC
                        </option>
                        <option value="speicherbetreiber" className="bg-bg text-white">
                          Speicherbetreiber
                        </option>
                        <option value="netzbetreiber" className="bg-bg text-white">
                          Netzbetreiber
                        </option>
                      </select>
                    </div>
                  </div>

                  <PreferenceRow
                    title="Check-Entwuerfe wiederherstellen"
                    description="Merkt laufende Eingaben lokal, damit mobile Sessions nach Reload oder Unterbrechung weitergefuehrt werden koennen."
                    checked={preferences.persistCheckDraft}
                    onCheckedChange={(checked) =>
                      setPreferences((current) => ({ ...current, persistCheckDraft: checked }))
                    }
                  />

                  <PreferenceRow
                    title="Projekt- und Dashboard-Karten kompakter anzeigen"
                    description="Verdichtet Listenansichten fuer kleinere Screens und groessere Arbeitsmengen."
                    checked={preferences.compactProjectCards}
                    onCheckedChange={(checked) =>
                      setPreferences((current) => ({ ...current, compactProjectCards: checked }))
                    }
                  />

                  <div className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                    <div>
                      <p className="text-sm font-medium text-white">Speicherort</p>
                      <p className="mt-1 text-sm leading-6 text-text-muted">
                        Diese Optionen bleiben absichtlich lokal im Browser und veraendern keine Backend-Daten.
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="outline"
                      className="h-11 rounded-xl border-border/70 bg-transparent text-white hover:bg-white/5"
                      onClick={onResetPreferences}
                    >
                      Standardwerte wiederherstellen
                    </Button>
                  </div>

                  <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
                    <p className="text-sm text-text-muted">
                      {preferencesReady && preferencesDirty
                        ? "Lokale Aenderungen sind noch nicht gespeichert."
                        : "Lokale Voreinstellungen sind aktiv."}
                    </p>
                    <Button
                      type="submit"
                      disabled={!preferencesReady || !preferencesDirty}
                      className="h-11 rounded-xl bg-brand-cyan px-5 text-black hover:bg-brand-cyan/90"
                    >
                      Arbeitsbereich speichern
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>

            <Card className={cardClass}>
              <CardHeader className="gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-brand-mint">
                    <LockKeyhole className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-white">Sicherheit</CardTitle>
                    <CardDescription className="text-text-muted">
                      Passwortwechsel mit Mindestpruefung und Bestaetigung.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <form onSubmit={onChangePassword} className="space-y-5">
                  <div className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3">
                    <div>
                      <p className="text-sm font-medium text-white">Passwortfelder anzeigen</p>
                      <p className="mt-1 text-sm text-text-muted">Hilfreich auf kleineren Screens oder bei komplexen Passwortregeln.</p>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="h-10 w-10 rounded-xl text-white hover:bg-white/10"
                      onClick={() => setShowPasswords((current) => !current)}
                    >
                      {showPasswords ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      <span className="sr-only">Passwortsichtbarkeit umschalten</span>
                    </Button>
                  </div>

                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2 md:col-span-2">
                      <Label htmlFor="current-password" className="text-white">
                        Aktuelles Passwort
                      </Label>
                      <Input
                        id="current-password"
                        type={showPasswords ? "text" : "password"}
                        value={currentPassword}
                        onChange={(event) => setCurrentPassword(event.target.value)}
                        className={fieldClass}
                        placeholder="Aktuelles Passwort"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="new-password" className="text-white">
                        Neues Passwort
                      </Label>
                      <Input
                        id="new-password"
                        type={showPasswords ? "text" : "password"}
                        value={newPassword}
                        onChange={(event) => setNewPassword(event.target.value)}
                        className={fieldClass}
                        placeholder="Mindestens 8 Zeichen"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="confirm-password" className="text-white">
                        Neues Passwort bestaetigen
                      </Label>
                      <Input
                        id="confirm-password"
                        type={showPasswords ? "text" : "password"}
                        value={confirmPassword}
                        onChange={(event) => setConfirmPassword(event.target.value)}
                        className={fieldClass}
                        placeholder="Neues Passwort wiederholen"
                      />
                    </div>
                  </div>

                  <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                    <p className="text-sm font-medium text-white">Pruefung</p>
                    <div className="mt-3 grid gap-2 sm:grid-cols-2">
                      {passwordChecks.map((check) => (
                        <div
                          key={check.label}
                          className={`rounded-xl border px-3 py-2 text-sm ${
                            check.ok
                              ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
                              : "border-white/10 bg-white/5 text-text-muted"
                          }`}
                        >
                          {check.label}
                        </div>
                      ))}
                    </div>
                  </div>

                  <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
                    <p className="text-sm text-text-muted">
                      Der Wechsel wirkt nach erfolgreicher Serverantwort und aendert keine weiteren lokalen Einstellungen.
                    </p>
                    <Button
                      type="submit"
                      disabled={!canSavePassword}
                      className="h-11 rounded-xl bg-brand-mint px-5 text-black hover:bg-brand-mint/90"
                    >
                      {passwordMutation.isPending ? "Passwort wird aktualisiert..." : "Passwort speichern"}
                    </Button>
                  </div>
                </form>
              </CardContent>
            </Card>
          </div>

          <div className="space-y-6">
            <Card className={cardClass}>
              <CardHeader className="gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-brand-cyan">
                    <ShieldCheck className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-white">Konto-Ueberblick</CardTitle>
                    <CardDescription className="text-text-muted">
                      Aktuelle Kontoinformationen und Wirkung der Einstellungen.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.2em] text-text-dim">Konto</div>
                  <div className="mt-2 text-lg font-semibold text-white">
                    {trimmedFullName || meQuery.data?.email || "Benutzerkonto"}
                  </div>
                  <div className="mt-1 text-sm text-text-muted">{meQuery.data?.email ?? "Nicht geladen"}</div>
                </div>
                <Separator className="bg-white/10" />
                <dl className="space-y-3 text-sm">
                  <div className="flex items-start justify-between gap-3">
                    <dt className="text-text-dim">Startansicht</dt>
                    <dd className="text-right text-white">
                      {preferences.defaultLandingTab === "dashboard" ? "Netzbetreiber-Dashboard" : "Netzanschluss-Check"}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="text-text-dim">Kundentyp-Vorgabe</dt>
                    <dd className="text-right text-white">
                      {preferences.defaultCustomerType ? preferences.defaultCustomerType : "Keine Vorauswahl"}
                    </dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="text-text-dim">Entwurfswiederherstellung</dt>
                    <dd className="text-right text-white">{preferences.persistCheckDraft ? "Aktiv" : "Deaktiviert"}</dd>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <dt className="text-text-dim">Listenmodus</dt>
                    <dd className="text-right text-white">
                      {preferences.compactProjectCards ? "Kompakt" : "Komfortabel"}
                    </dd>
                  </div>
                </dl>
              </CardContent>
            </Card>

            <Card className={cardClass}>
              <CardHeader className="gap-3">
                <div className="flex items-center gap-3">
                  <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-brand-orange">
                    <LogOut className="h-5 w-5" />
                  </div>
                  <div>
                    <CardTitle className="text-white">Sitzung</CardTitle>
                    <CardDescription className="text-text-muted">
                      Aktuelle Sitzung beenden, ohne lokale Einstellungen zu verlieren.
                    </CardDescription>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-sm leading-6 text-text-muted">
                  Logout beendet die aktuelle Session. Ihre lokalen Workflow-Vorgaben bleiben auf diesem Geraet erhalten.
                </div>
                <Button
                  type="button"
                  onClick={onLogout}
                  disabled={isLoggingOut}
                  className="h-11 w-full rounded-xl bg-white/10 text-white hover:bg-white/15"
                >
                  {isLoggingOut ? "Meldet ab..." : "Abmelden"}
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
  );
}
