"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, ShieldCheck, UserRound } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { me, type AuthUser } from "@/lib/api/auth";
import { approveNetzbetreiber, listPendingNetzbetreiber, type AdminVnbUser } from "@/lib/api/admin-users";

const cardClass = "rounded-[24px] border border-border/70 bg-bg-card/80 p-6 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";

export default function AdminUsersPage() {
  const queryClient = useQueryClient();
  const [notice, setNotice] = useState<{ tone: "success" | "error"; text: string } | null>(null);

  const meQuery = useQuery<AuthUser>({
    queryKey: ["me"],
    queryFn: me,
  });

  const pendingQuery = useQuery<AdminVnbUser[]>({
    queryKey: ["admin-pending-vnb"],
    queryFn: listPendingNetzbetreiber,
    enabled: meQuery.data?.role === "admin",
  });

  useEffect(() => {
    if (meQuery.isError) {
      window.location.href = "/login?next=/admin/users";
    }
  }, [meQuery.isError]);

  const approveMutation = useMutation({
    mutationFn: (userId: number) => approveNetzbetreiber(userId),
    onSuccess: () => {
      setNotice({ tone: "success", text: "Netzbetreiber-Konto freigeschaltet." });
      void queryClient.invalidateQueries({ queryKey: ["admin-pending-vnb"] });
    },
    onError: (err: Error) => {
      setNotice({ tone: "error", text: err.message });
    },
  });

  if (meQuery.isLoading) {
    return (
      <main className="min-h-screen bg-bg text-white">
        <Header />
        <div className="mx-auto max-w-4xl px-4 py-10 text-text-muted">Lade Admin-Bereich…</div>
      </main>
    );
  }

  if (meQuery.data?.role !== "admin") {
    return (
      <main className="min-h-screen bg-bg text-white">
        <Header />
        <div className="mx-auto max-w-4xl px-4 py-10">
          <div className={cardClass}>
            <h1 className="text-2xl font-semibold text-white">Kein Zugriff</h1>
            <p className="mt-2 text-sm text-text-muted">
              Diese Seite ist nur fuer Administratoren. Alternativ:{" "}
              <code className="text-brand-cyan">scripts/approve_netzbetreiber.py</code>
            </p>
            <Link href="/settings" className="mt-4 inline-block text-sm text-brand-cyan hover:underline">
              Zurueck zu Settings
            </Link>
          </div>
        </div>
      </main>
    );
  }

  const pending = pendingQuery.data ?? [];

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="mx-auto max-w-4xl space-y-6 px-4 py-8 sm:px-6">
        <div className={cardClass}>
          <div className="inline-flex items-center gap-2 rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] text-brand-cyan">
            <ShieldCheck className="h-3.5 w-3.5" />
            Admin
          </div>
          <h1 className="mt-4 text-3xl font-semibold text-white">Netzbetreiber freischalten</h1>
          <p className="mt-2 text-sm leading-6 text-text-muted">
            Konten mit Rolle <strong className="text-white">netzbetreiber</strong> und Status{" "}
            <strong className="text-white">pending</strong> erhalten Zugang zu Dashboard und Kommunikation nach Freigabe.
          </p>
        </div>

        {notice ? (
          <div
            className={`rounded-2xl border px-4 py-3 text-sm ${
              notice.tone === "success"
                ? "border-green-500/30 bg-green-500/10 text-green-200"
                : "border-red-500/30 bg-red-500/10 text-red-200"
            }`}
          >
            {notice.text}
          </div>
        ) : null}

        <div className={cardClass}>
          <h2 className="text-lg font-semibold text-white">Ausstehende Freigaben</h2>
          {pendingQuery.isLoading ? (
            <p className="mt-4 text-sm text-text-muted">Lade Liste…</p>
          ) : pending.length === 0 ? (
            <p className="mt-4 text-sm text-text-muted">Keine ausstehenden Netzbetreiber-Anfragen.</p>
          ) : (
            <ul className="mt-4 space-y-3">
              {pending.map((user) => (
                <li
                  key={user.id}
                  className="flex flex-col gap-3 rounded-2xl border border-white/10 bg-white/5 p-4 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="flex items-start gap-3">
                    <UserRound className="mt-0.5 h-5 w-5 shrink-0 text-brand-cyan" />
                    <div>
                      <p className="font-medium text-white">{user.email}</p>
                      <p className="text-xs text-text-muted">
                        ID {user.id}
                        {user.full_name ? ` · ${user.full_name}` : ""} · Status: {user.vnb_verification_status}
                      </p>
                    </div>
                  </div>
                  <Button
                    type="button"
                    disabled={approveMutation.isPending}
                    onClick={() => approveMutation.mutate(user.id)}
                    className="h-10 shrink-0 rounded-xl bg-brand-orange text-white hover:bg-brand-orangeHover"
                  >
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Freischalten
                  </Button>
                </li>
              ))}
            </ul>
          )}
        </div>

        <p className="text-xs text-text-dim">
          CLI-Alternative: <code>python scripts/approve_netzbetreiber.py --email …</code> (siehe docs/VNB_ACCESS.md).
        </p>
      </div>
    </main>
  );
}
