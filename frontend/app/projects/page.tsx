"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { Header } from "@/components/Header";
import { createProject, deleteProject, listProjects, Project } from "@/lib/api/projects";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

export default function ProjectsPage() {
  const [name, setName] = useState("");
  const [plz, setPlz] = useState("");
  const [typ, setTyp] = useState("pv");
  const [leistungKw, setLeistungKw] = useState("1000");
  const [uiMessage, setUiMessage] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const projectsQuery = useQuery<Project[]>({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  useEffect(() => {
    if (projectsQuery.isError) {
      window.location.href = "/login";
    }
  }, [projectsQuery.isError]);

  const createMutation = useMutation({
    mutationFn: createProject,
    onSuccess: () => {
      setName("");
      setPlz("");
      setUiMessage("Projekt erstellt.");
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: deleteProject,
    onSuccess: () => {
      setUiMessage("Projekt geloescht.");
      queryClient.invalidateQueries({ queryKey: ["projects"] });
    },
  });

  async function onCreate(e: FormEvent) {
    e.preventDefault();
    await createMutation.mutateAsync({ name, plz, typ, leistung_kw: Number(leistungKw) });
  }

  async function onDelete(projectId: number) {
    await deleteMutation.mutateAsync(projectId);
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="max-w-4xl mx-auto p-6 space-y-8">
        <section>
          <h1 className="text-2xl font-semibold mb-4">Projekte</h1>
          {uiMessage ? <div className="mb-3 text-sm text-brand-cyan">{uiMessage}</div> : null}
          <form onSubmit={onCreate} className="grid grid-cols-1 md:grid-cols-5 gap-2">
            <input className="p-2 rounded bg-bg-elev" placeholder="Projektname" value={name} onChange={(e) => setName(e.target.value)} required />
            <input className="p-2 rounded bg-bg-elev" placeholder="PLZ" value={plz} onChange={(e) => setPlz(e.target.value)} required />
            <input className="p-2 rounded bg-bg-elev" placeholder="Typ" value={typ} onChange={(e) => setTyp(e.target.value)} required />
            <input className="p-2 rounded bg-bg-elev" placeholder="Leistung kW" value={leistungKw} onChange={(e) => setLeistungKw(e.target.value)} required />
            <button className="bg-brand-orange rounded p-2 font-semibold">Erstellen</button>
          </form>
        </section>

        <section className="space-y-3">
          {projectsQuery.isLoading ? (
            <div className="p-4 rounded border border-border bg-bg-elev text-sm text-text-muted">Lade Projekte...</div>
          ) : null}
          {projectsQuery.isError ? (
            <div className="p-4 rounded border border-red-500/30 bg-red-500/10 text-sm text-red-300">
              Projekte konnten nicht geladen werden. Bitte erneut einloggen.
            </div>
          ) : null}
          {(projectsQuery.data ?? []).map((project) => (
            <div key={project.id} className="p-4 rounded border border-border bg-bg-elev flex items-center justify-between">
              <div>
                <p className="font-semibold">{project.name}</p>
                <p className="text-sm text-text-muted">{project.typ} · {project.plz} · {project.leistung_kw} kW</p>
              </div>
              <div className="flex gap-3 items-center">
                <Link href={`/projects/${project.id}`} className="text-brand-cyan text-sm">Bearbeiten</Link>
                <button onClick={() => onDelete(project.id)} className="text-red-400 text-sm">Loeschen</button>
              </div>
            </div>
          ))}
        </section>
      </div>
    </main>
  );
}
