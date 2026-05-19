"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageSquarePlus, MessagesSquare, ShieldAlert } from "lucide-react";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import {
  createVnbThread,
  getVnbThread,
  listVnbThreads,
  postVnbThreadMessage,
  VNB_COMMS_CATEGORY_LABELS,
  type VnbCommsCategory,
  type VnbThreadDetail,
  type VnbThreadSummary,
} from "@/lib/api/vnb-comms";

const CATEGORIES: VnbCommsCategory[] = ["kapazitaetshinweis", "redispatch", "infrastruktur", "sonstiges"];

function fmt(ts?: string | null) {
  if (!ts) return "—";
  try {
    return new Date(ts).toLocaleString("de-DE");
  } catch {
    return ts;
  }
}

export default function VnbKommunikationPage() {
  const queryClient = useQueryClient();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [replyBody, setReplyBody] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [createTitle, setCreateTitle] = useState("");
  const [createCategory, setCreateCategory] = useState<VnbCommsCategory>("kapazitaetshinweis");
  const [createRegion, setCreateRegion] = useState("");
  const [createBody, setCreateBody] = useState("");
  const [error, setError] = useState<string | null>(null);

  const threadsQuery = useQuery({
    queryKey: ["vnb-comms-threads"],
    queryFn: () => listVnbThreads(),
  });

  const threadQuery = useQuery({
    queryKey: ["vnb-comms-thread", selectedId],
    queryFn: () => getVnbThread(selectedId as number),
    enabled: selectedId != null,
  });

  const createMutation = useMutation({
    mutationFn: () =>
      createVnbThread({
        title: createTitle,
        category: createCategory,
        body: createBody,
        target_vnb_region: createRegion.trim() || undefined,
      }),
    onSuccess: (thread) => {
      setShowCreate(false);
      setCreateTitle("");
      setCreateBody("");
      setCreateRegion("");
      setSelectedId(thread.id);
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["vnb-comms-threads"] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const replyMutation = useMutation({
    mutationFn: () => postVnbThreadMessage(selectedId as number, replyBody),
    onSuccess: () => {
      setReplyBody("");
      setError(null);
      void queryClient.invalidateQueries({ queryKey: ["vnb-comms-threads"] });
      void queryClient.invalidateQueries({ queryKey: ["vnb-comms-thread", selectedId] });
    },
    onError: (err: Error) => setError(err.message),
  });

  const threads = threadsQuery.data ?? [];
  const activeThread: VnbThreadDetail | VnbThreadSummary | undefined = threadQuery.data ?? threads.find((t) => t.id === selectedId);

  const sortedThreads = useMemo(
    () => [...threads].sort((a, b) => String(b.last_message_at || b.created_at).localeCompare(String(a.last_message_at || a.created_at))),
    [threads],
  );

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <section className="mx-auto max-w-6xl px-4 py-8 sm:px-6">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-brand-cyan">NB-Austausch</p>
            <h1 className="mt-2 text-3xl font-semibold tracking-tight">Kommunikation zwischen Netzbetreibern</h1>
            <p className="mt-2 max-w-2xl text-sm leading-6 text-text-muted">
              Geschuetzter fachlicher Austausch im Board „Austausch“. Keine oeffentliche Sichtbarkeit, keine
              Kapazitaetszusage.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <Link
              href="/vnb"
              className="inline-flex items-center rounded-2xl border border-white/10 px-4 py-2 text-sm font-semibold text-white hover:bg-white/5"
            >
              VNB-Dashboard
            </Link>
            <Button type="button" onClick={() => setShowCreate((v) => !v)} className="rounded-2xl">
              <MessageSquarePlus className="mr-2 h-4 w-4" />
              Neuer Thread
            </Button>
          </div>
        </div>

        <div className="mb-6 rounded-2xl border border-brand-orange/25 bg-brand-orange/10 px-4 py-3 text-sm leading-6 text-text-muted">
          <p className="flex items-center gap-2 font-medium text-white">
            <ShieldAlert className="h-4 w-4 text-brand-orange" />
            Hinweis
          </p>
          <p className="mt-1">
            Vorlaeufiger Austausch unter Netzbetreibern. Keine Kapazitaetsgarantie, keine Netzanschlusszusage. Keine
            Endkunden-PII (E-Mail/Telefon) ohne Rechtsgrundlage. Nachrichten sind revisionssicher protokolliert.
          </p>
        </div>

        {error ? (
          <p className="mb-4 rounded-xl border border-red-500/40 bg-red-950/40 px-4 py-3 text-sm text-red-200">{error}</p>
        ) : null}

        {showCreate ? (
          <Card className="mb-6 border-white/10 bg-white/5">
            <CardHeader>
              <CardTitle>Neuer Thread im Austausch-Board</CardTitle>
              <CardDescription>Betreff, Kategorie und erste Nachricht.</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <label className="block text-sm">
                <span className="text-text-muted">Betreff</span>
                <input
                  className="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                  value={createTitle}
                  onChange={(e) => setCreateTitle(e.target.value)}
                  maxLength={200}
                />
              </label>
              <label className="block text-sm">
                <span className="text-text-muted">Kategorie</span>
                <select
                  className="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                  value={createCategory}
                  onChange={(e) => setCreateCategory(e.target.value as VnbCommsCategory)}
                >
                  {CATEGORIES.map((c) => (
                    <option key={c} value={c}>
                      {VNB_COMMS_CATEGORY_LABELS[c]}
                    </option>
                  ))}
                </select>
              </label>
              <label className="block text-sm">
                <span className="text-text-muted">Region (optional)</span>
                <input
                  className="mt-1 w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                  value={createRegion}
                  onChange={(e) => setCreateRegion(e.target.value)}
                  placeholder="z. B. Westfalen, Bayern"
                />
              </label>
              <label className="block text-sm">
                <span className="text-text-muted">Nachricht</span>
                <textarea
                  className="mt-1 min-h-[120px] w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                  value={createBody}
                  onChange={(e) => setCreateBody(e.target.value)}
                />
              </label>
              <div className="flex gap-2">
                <Button type="button" disabled={createMutation.isPending} onClick={() => createMutation.mutate()}>
                  Thread anlegen
                </Button>
                <Button type="button" variant="outline" onClick={() => setShowCreate(false)}>
                  Abbrechen
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : null}

        <div className="grid gap-6 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
          <Card className="border-white/10 bg-white/5">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-lg">
                <MessagesSquare className="h-5 w-5 text-brand-cyan" />
                Threads
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {threadsQuery.isLoading ? <p className="text-sm text-text-muted">Lade Threads...</p> : null}
              {!threadsQuery.isLoading && sortedThreads.length === 0 ? (
                <p className="text-sm text-text-muted">Noch keine Threads. Legen Sie den ersten Hinweis an.</p>
              ) : null}
              {sortedThreads.map((thread) => (
                <button
                  key={thread.id}
                  type="button"
                  onClick={() => setSelectedId(thread.id)}
                  className={`w-full rounded-2xl border px-4 py-3 text-left transition ${
                    selectedId === thread.id
                      ? "border-brand-cyan/40 bg-brand-cyan/10"
                      : "border-white/10 bg-black/10 hover:bg-black/20"
                  }`}
                >
                  <p className="text-sm font-semibold text-white">{thread.title}</p>
                  <p className="mt-1 text-xs text-text-muted">
                    {VNB_COMMS_CATEGORY_LABELS[thread.category]}
                    {thread.target_vnb_region ? ` · ${thread.target_vnb_region}` : ""}
                    {" · "}
                    {fmt(thread.last_message_at || thread.created_at)}
                  </p>
                  {thread.last_message_preview ? (
                    <p className="mt-2 line-clamp-2 text-xs text-slate-400">{thread.last_message_preview}</p>
                  ) : null}
                </button>
              ))}
            </CardContent>
          </Card>

          <Card className="border-white/10 bg-white/5">
            <CardHeader>
              <CardTitle>Thread-Detail</CardTitle>
              <CardDescription>
                {selectedId ? `Thread #${selectedId}` : "Waehlen Sie links einen Thread oder legen Sie einen neuen an."}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {!selectedId ? (
                <p className="text-sm text-text-muted">Kein Thread ausgewaehlt.</p>
              ) : threadQuery.isLoading ? (
                <p className="text-sm text-text-muted">Lade Nachrichten...</p>
              ) : (
                <div className="space-y-4">
                  {activeThread && "messages" in activeThread
                    ? activeThread.messages.map((msg) => (
                        <article key={msg.id} className="rounded-2xl border border-white/10 bg-black/15 px-4 py-3">
                          <p className="text-xs text-text-muted">
                            Nutzer #{msg.sender_user_id} · {fmt(msg.created_at)}
                          </p>
                          <p className="mt-2 whitespace-pre-wrap text-sm leading-6 text-slate-200">{msg.body}</p>
                        </article>
                      ))
                    : null}
                  <div className="border-t border-white/10 pt-4">
                    <label className="block text-sm text-text-muted">Antwort</label>
                    <textarea
                      className="mt-1 min-h-[100px] w-full rounded-xl border border-white/10 bg-black/20 px-3 py-2"
                      value={replyBody}
                      onChange={(e) => setReplyBody(e.target.value)}
                    />
                    <Button
                      type="button"
                      className="mt-3"
                      disabled={replyMutation.isPending || !replyBody.trim()}
                      onClick={() => replyMutation.mutate()}
                    >
                      Antwort senden
                    </Button>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </section>
    </main>
  );
}
