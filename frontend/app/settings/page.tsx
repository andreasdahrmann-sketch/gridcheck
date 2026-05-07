"use client";

import { FormEvent, useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { getCsrfTokenFromCookie } from "@/lib/api/csrf";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

type Me = { id: number; email: string; role: string; full_name?: string | null };

export default function SettingsPage() {
  const queryClient = useQueryClient();
  const [fullName, setFullName] = useState("");
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [uiMessage, setUiMessage] = useState<string | null>(null);

  const meQuery = useQuery<Me>({
    queryKey: ["me"],
    queryFn: async () => {
      const res = await fetch("/api/backend/api/v1/users/me", { credentials: "include", cache: "no-store" });
      if (!res.ok) throw new Error("not-authorized");
      return res.json();
    },
  });

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
      if (!res.ok) throw new Error("save-failed");
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["me"] });
      setUiMessage("Profil aktualisiert.");
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
      if (!res.ok) throw new Error("password-failed");
      return res.json();
    },
    onSuccess: () => {
      setCurrentPassword("");
      setNewPassword("");
      setUiMessage("Passwort geaendert.");
    },
  });

  async function onSaveProfile(e: FormEvent) {
    e.preventDefault();
    await profileMutation.mutateAsync(fullName);
  }

  async function onChangePassword(e: FormEvent) {
    e.preventDefault();
    await passwordMutation.mutateAsync({ currentPassword, newPassword });
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="max-w-2xl mx-auto p-6 space-y-8">
        <h1 className="text-2xl font-semibold">Einstellungen</h1>
        {uiMessage ? <div className="text-sm text-brand-cyan">{uiMessage}</div> : null}
        {meQuery.isLoading ? (
          <div className="p-4 rounded border border-border bg-bg-elev text-sm text-text-muted">Lade Profil...</div>
        ) : null}
        {meQuery.isError ? (
          <div className="p-4 rounded border border-red-500/30 bg-red-500/10 text-sm text-red-300">
            Profil konnte nicht geladen werden.
          </div>
        ) : null}
        <p className="text-sm text-text-muted">{meQuery.data?.email} · Rolle: {meQuery.data?.role}</p>
        <form onSubmit={onSaveProfile} className="space-y-3">
          <h2 className="font-semibold">Profil</h2>
          <input className="w-full p-2 rounded bg-bg-elev" value={fullName} onChange={(e) => setFullName(e.target.value)} />
          <button className="bg-brand-orange rounded p-2 px-4 font-semibold">Profil speichern</button>
        </form>
        <form onSubmit={onChangePassword} className="space-y-3">
          <h2 className="font-semibold">Passwort</h2>
          <input type="password" className="w-full p-2 rounded bg-bg-elev" placeholder="Aktuelles Passwort" value={currentPassword} onChange={(e) => setCurrentPassword(e.target.value)} />
          <input type="password" className="w-full p-2 rounded bg-bg-elev" placeholder="Neues Passwort" value={newPassword} onChange={(e) => setNewPassword(e.target.value)} />
          <button className="bg-brand-mint text-black rounded p-2 px-4 font-semibold">Passwort speichern</button>
        </form>
      </div>
    </main>
  );
}
