"use client";

import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Clock3, ShieldCheck, UserRound, Zap } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { me, type AuthUser } from "@/lib/api/auth";
import {
  claimOpsFollowup,
  listOpsFollowups,
  updateOpsFollowupStatus,
  type OpsFollowup,
} from "@/lib/api/ops-followups";

const cardClass = "rounded-[24px] border border-border/70 bg-bg-card/80 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";

type Notice =
  | {
      tone: "success" | "error";
      text: string;
    }
  | null;

function fmt(ts?: string | null) {
  if (!ts) return "offen";
  try {
    return new Date(ts).toLocaleString("de-DE");
  } catch {
    return ts;
  }
}

export default function OpsPage() {
  const queryClient = useQueryClient();
  const [includeCompleted, setIncludeCompleted] = useState(false);
  const [assignedToMe, setAssignedToMe] = useState(false);
  const [notice, setNotice] = useState<Notice>(null);
  const [comments, setComments] = useState<Record<number, string>>({});

  const meQuery = useQuery<AuthUser>({
    queryKey: ["me"],
    queryFn: me,
  });

  const followupsQuery = useQuery<OpsFollowup[]>({
    queryKey: ["ops-followups", includeCompleted, assignedToMe],
    queryFn: () => listOpsFollowups({ includeCompleted, assignedToMe, limit: 100 }),
    enabled: meQuery.data?.role === "admin",
  });

  useEffect(() => {
    if (meQuery.isError) {
      window.location.href = "/login";
    }
  }, [meQuery.isError]);

  const claimMutation = useMutation({
    mutationFn: ({ entitlementId, comment }: { entitlementId: number; comment?: string }) =>
      claimOpsFollowup(entitlementId, comment),
    onSuccess: () => {
      setNotice({ tone: "success", text: "OPS-Follow-up wurde uebernommen und auf in Bearbeitung gesetzt." });
      void queryClient.invalidateQueries({ queryKey: ["ops-followups"] });
    },
    onError: (error) => {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Follow-up konnte nicht uebernommen werden." });
    },
  });

  const statusMutation = useMutation({
    mutationFn: ({ entitlementId, status, comment }: { entitlementId: number; status: "in_progress" | "completed"; comment?: string }) =>
      updateOpsFollowupStatus(entitlementId, status, comment),
    onSuccess: (_, variables) => {
      setNotice({
        tone: "success",
        text:
          variables.status === "completed"
            ? "OPS-Follow-up wurde abgeschlossen."
            : "OPS-Follow-up ist jetzt in Bearbeitung.",
      });
      void queryClient.invalidateQueries({ queryKey: ["ops-followups"] });
    },
    onError: (error) => {
      setNotice({ tone: "error", text: error instanceof Error ? error.message : "Status konnte nicht aktualisiert werden." });
    },
  });

  const summary = useMemo(() => {
    const items = followupsQuery.data ?? [];
    return {
      total: items.length,
      pending: items.filter((item) => item.ops_status === "pending_review").length,
      inProgress: items.filter((item) => item.ops_status === "in_progress").length,
      express: items.filter((item) => item.express_requested).length,
    };
  }, [followupsQuery.data]);

  if (meQuery.isLoading) {
    return (
      <main className="min-h-screen bg-bg text-white">
        <Header />
        <div className="mx-auto max-w-6xl px-4 py-8 sm:px-6">Profil wird geladen...</div>
      </main>
    );
  }

  if (meQuery.data?.role !== "admin") {
    return (
      <main className="min-h-screen bg-bg text-white">
        <Header />
        <div className="mx-auto max-w-4xl px-4 py-8 sm:px-6">
          <Card className={cardClass}>
            <CardHeader>
              <CardTitle className="text-white">Interner OPS-Bereich</CardTitle>
              <CardDescription className="text-text-muted">
                Dieser Bereich ist nur fuer interne Admin-Nutzer freigeschaltet.
              </CardDescription>
            </CardHeader>
          </Card>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <section className="flex flex-col gap-3 border-b border-border/70 pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-[0.24em] text-brand-cyan">Interner Workflow</p>
            <h1 className="mt-2 text-3xl font-semibold text-white">OPS-Follow-ups</h1>
            <p className="mt-3 max-w-3xl text-sm leading-6 text-text-muted">
              Bearbeitungspfad fuer Professional- und Express-Nachlauf mit klarer Zuweisung, Statusfolge und Audit-Trail.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => setAssignedToMe((current) => !current)}
              className={`rounded-full border px-4 py-2 text-sm ${
                assignedToMe ? "border-brand-cyan/30 bg-brand-cyan/10 text-white" : "border-white/10 bg-white/5 text-text-muted"
              }`}
            >
              Nur meine Follow-ups
            </button>
            <button
              type="button"
              onClick={() => setIncludeCompleted((current) => !current)}
              className={`rounded-full border px-4 py-2 text-sm ${
                includeCompleted ? "border-brand-cyan/30 bg-brand-cyan/10 text-white" : "border-white/10 bg-white/5 text-text-muted"
              }`}
            >
              Abgeschlossene einblenden
            </button>
          </div>
        </section>

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

        <div className="mt-6 grid gap-4 md:grid-cols-4">
          {[
            { label: "Offen gesamt", value: summary.total, icon: ShieldCheck },
            { label: "Review ausstehend", value: summary.pending, icon: Clock3 },
            { label: "In Bearbeitung", value: summary.inProgress, icon: UserRound },
            { label: "Express-Faelle", value: summary.express, icon: Zap },
          ].map((item) => (
            <Card key={item.label} className={cardClass}>
              <CardContent className="flex items-center justify-between px-5 py-5">
                <div>
                  <p className="text-sm text-text-muted">{item.label}</p>
                  <p className="mt-2 text-2xl font-semibold text-white">{item.value}</p>
                </div>
                <item.icon className="h-5 w-5 text-brand-cyan" />
              </CardContent>
            </Card>
          ))}
        </div>

        <div className="mt-6">
          {followupsQuery.isLoading ? (
            <div className="rounded-2xl border border-border/70 bg-bg-card/80 px-4 py-4 text-sm text-text-muted">
              OPS-Queue wird geladen...
            </div>
          ) : followupsQuery.isError ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-4 text-sm text-red-300">
              OPS-Queue konnte nicht geladen werden.
            </div>
          ) : followupsQuery.data && followupsQuery.data.length > 0 ? (
            <div className="grid gap-4">
              {followupsQuery.data.map((item) => {
                const note = comments[item.entitlement_id] ?? item.ops_last_comment ?? "";
                const isOwnedByOther =
                  item.ops_assignee_user_id != null && item.ops_assignee_user_id !== meQuery.data?.id;
                const isBusy =
                  claimMutation.isPending || statusMutation.isPending;
                return (
                  <Card key={item.entitlement_id} className={cardClass}>
                    <CardContent className="space-y-4 px-5 py-5">
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div>
                          <div className="flex flex-wrap items-center gap-2">
                            <span className="rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-medium text-brand-cyan">
                              {item.offer_id}
                            </span>
                            <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-white">
                              OPS {item.ops_status}
                            </span>
                            {item.express_requested ? (
                              <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-xs text-amber-100">
                                Express
                              </span>
                            ) : null}
                          </div>
                          <p className="mt-3 text-lg font-semibold text-white">
                            {item.customer_name || item.customer_email || `User ${item.customer_user_id}`}
                          </p>
                          <p className="mt-1 text-sm text-text-muted">
                            {item.project_name ? `Projekt ${item.project_name} · ` : ""}
                            Scope {item.package_scope} · Run {item.analysis_run_id ?? "n/a"}
                          </p>
                        </div>
                        <div className="text-sm text-text-muted lg:text-right">
                          <p>Zugewiesen an {item.ops_assignee_name || item.ops_assignee_email || "niemanden"}</p>
                          <p className="mt-1">Aktualisiert {fmt(item.updated_at)}</p>
                        </div>
                      </div>

                      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                        <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                          <p className="text-xs uppercase tracking-[0.16em] text-text-dim">Naechste Aktion</p>
                          <p className="mt-2 text-sm text-white">{item.next_action}</p>
                        </div>
                        <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                          <p className="text-xs uppercase tracking-[0.16em] text-text-dim">Claim</p>
                          <p className="mt-2 text-sm text-white">{fmt(item.ops_assigned_at)}</p>
                        </div>
                        <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                          <p className="text-xs uppercase tracking-[0.16em] text-text-dim">Bearbeitung gestartet</p>
                          <p className="mt-2 text-sm text-white">{fmt(item.ops_started_at)}</p>
                        </div>
                        <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                          <p className="text-xs uppercase tracking-[0.16em] text-text-dim">Checkout-Session</p>
                          <p className="mt-2 text-sm text-white">{item.checkout_session_id || "n/a"}</p>
                        </div>
                      </div>

                      <div className="space-y-2">
                        <label className="text-sm font-medium text-white" htmlFor={`ops-comment-${item.entitlement_id}`}>
                          Bearbeitungskommentar
                        </label>
                        <textarea
                          id={`ops-comment-${item.entitlement_id}`}
                          value={note}
                          onChange={(event) =>
                            setComments((current) => ({ ...current, [item.entitlement_id]: event.target.value }))
                          }
                          className="min-h-[96px] w-full rounded-2xl border border-border/70 bg-white/5 px-4 py-3 text-sm text-white outline-none transition focus:border-brand-cyan/70"
                          placeholder="Interne Notiz, naechster Schritt oder Abschlussvermerk"
                        />
                      </div>

                      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        <p className={`text-sm ${isOwnedByOther ? "text-amber-100" : "text-text-muted"}`}>
                          {isOwnedByOther
                            ? "Dieser Follow-up ist bereits einem anderen Admin zugewiesen."
                            : item.ops_status === "completed"
                              ? "Abgeschlossen."
                              : "Nur zugewiesene oder unzugewiesene Follow-ups koennen bearbeitet werden."}
                        </p>
                        <div className="flex flex-col gap-2 sm:flex-row">
                          <Button
                            type="button"
                            variant="outline"
                            disabled={isBusy || isOwnedByOther || item.ops_status === "completed"}
                            className="h-11 rounded-xl border-border/70 bg-transparent text-white hover:bg-white/5"
                            onClick={() =>
                              claimMutation.mutate({ entitlementId: item.entitlement_id, comment: note.trim() || undefined })
                            }
                          >
                            Uebernehmen
                          </Button>
                          <Button
                            type="button"
                            disabled={isBusy || isOwnedByOther || item.ops_status !== "pending_review"}
                            className="h-11 rounded-xl bg-brand-cyan text-black hover:bg-brand-cyan/90"
                            onClick={() =>
                              statusMutation.mutate({
                                entitlementId: item.entitlement_id,
                                status: "in_progress",
                                comment: note.trim() || undefined,
                              })
                            }
                          >
                            In Bearbeitung
                          </Button>
                          <Button
                            type="button"
                            disabled={isBusy || isOwnedByOther || item.ops_status !== "in_progress"}
                            className="h-11 rounded-xl bg-brand-orange text-white hover:bg-brand-orangeHover"
                            onClick={() =>
                              statusMutation.mutate({
                                entitlementId: item.entitlement_id,
                                status: "completed",
                                comment: note.trim() || undefined,
                              })
                            }
                          >
                            Abschliessen
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          ) : (
            <div className="rounded-2xl border border-border/70 bg-bg-card/80 px-4 py-4 text-sm text-text-muted">
              Keine OPS-Follow-ups fuer die aktuelle Filterung gefunden.
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
