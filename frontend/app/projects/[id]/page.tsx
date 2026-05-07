"use client";

import { FormEvent, useEffect, useState } from "react";
import { Header } from "@/components/Header";
import { getProject, shareProject, updateProject } from "@/lib/api/projects";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  const projectId = Number(params.id);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [shareUserId, setShareUserId] = useState("");
  const [uiMessage, setUiMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });
  const project = projectQuery.data;

  const updateMutation = useMutation({
    mutationFn: (payload: { name: string; description: string }) =>
      updateProject(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      setUiMessage("Projekt gespeichert.");
    },
  });

  const shareMutation = useMutation({
    mutationFn: (userId: number) => shareProject(projectId, userId, "viewer"),
    onSuccess: () => {
      setShareUserId("");
      setUiMessage("Projekt geteilt.");
    },
  });

  useEffect(() => {
    if (projectQuery.isError) {
      window.location.href = "/login";
    }
  }, [projectQuery.isError]);

  async function onSave(e: FormEvent) {
    e.preventDefault();
    await updateMutation.mutateAsync({ name, description });
  }

  async function onShare(e: FormEvent) {
    e.preventDefault();
    if (!shareUserId) return;
    await shareMutation.mutateAsync(Number(shareUserId));
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="max-w-2xl mx-auto p-6 space-y-8">
        <h1 className="text-2xl font-semibold">Projekt bearbeiten</h1>
        {uiMessage ? <div className="text-sm text-brand-cyan">{uiMessage}</div> : null}
        {projectQuery.isLoading ? (
          <div className="p-4 rounded border border-border bg-bg-elev text-sm text-text-muted">Lade Projekt...</div>
        ) : null}
        {projectQuery.isError ? (
          <div className="p-4 rounded border border-red-500/30 bg-red-500/10 text-sm text-red-300">
            Projekt konnte nicht geladen werden.
          </div>
        ) : null}
        <form onSubmit={onSave} className="space-y-3">
          <input
            className="w-full p-2 rounded bg-bg-elev"
            value={name || project?.name || ""}
            onChange={(e) => setName(e.target.value)}
          />
          <textarea
            className="w-full p-2 rounded bg-bg-elev"
            rows={4}
            value={description || project?.description || ""}
            onChange={(e) => setDescription(e.target.value)}
          />
          <button className="bg-brand-orange rounded p-2 px-4 font-semibold">Speichern</button>
        </form>
        <form onSubmit={onShare} className="space-y-3">
          <h2 className="font-semibold">Projekt teilen</h2>
          <input className="w-full p-2 rounded bg-bg-elev" placeholder="User-ID" value={shareUserId} onChange={(e) => setShareUserId(e.target.value)} />
          <button className="bg-brand-mint text-black rounded p-2 px-4 font-semibold">Teilen</button>
        </form>
      </div>
    </main>
  );
}
