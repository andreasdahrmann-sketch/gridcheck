"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useEffect, useMemo, useState } from "react";
import { ArrowLeft, ClipboardList, FileDown, GitCompareArrows, MapPinned, Radar, Settings2, Share2 } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import BillingUpgradePrompt from "@/components/BillingUpgradePrompt";
import AnalysisProgressPanel from "@/components/analysis/AnalysisProgressPanel";
import { AnalysisDisclaimer } from "@/components/legal/AnalysisDisclaimer";
import NetzplanVisualization from "@/components/NetzplanVisualization";
import ProjectProfileFields from "@/components/ProjectProfileFields";
import ProductDecisionGuide from "@/components/billing/ProductDecisionGuide";
import { Header } from "@/components/Header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { buildSiteMarkerHref } from "@/lib/app-flow";
import { AnalyzeApiError, analyzeGridcheck, exportStakeholderPdf } from "@/lib/api/analyze";
import { downloadBlobFile } from "@/lib/download-blob";
import {
  createBillingCheckout,
  getBillingStatus,
  type BillingAnalysisOption,
  type BillingStatus,
} from "@/lib/api/billing";
import {
  getProject,
  shareProject,
  updateProject,
  type Project,
  type ProjectRoleInputs,
} from "@/lib/api/projects";
import {
  getOfferProfile,
  getPackageBoundaryWarnings,
  getPackageScopeLabel,
  getReportScopeLabel,
} from "@/lib/billing-product";
import { getProjectCommercialInsight } from "@/lib/project-commercial";
import {
  buildIndicativeCostBand,
  buildProjektiererGuidance,
  canViewDeepTechnicalDetails,
  getStakeholderProductCopy,
  resolveStakeholderProductPath,
} from "@/lib/stakeholder-product";
import { pushCompareSnapshot } from "@/lib/scenario-compare-snapshots";
import type { GridCheckInput, GridCheckResult, StakeholderContextInput } from "@/types";

const PROJECT_TYPE_OPTIONS = [
  { value: "pv", label: "PV" },
  { value: "wind", label: "Wind" },
  { value: "bess", label: "BESS" },
  { value: "ladepark", label: "Ladepark" },
  { value: "sonstiges", label: "Sonstiges" },
];

const cardClass = "rounded-[24px] border border-border/70 bg-bg-card/80 shadow-[0_12px_42px_rgba(0,0,0,0.18)]";
const fieldClass =
  "h-11 rounded-xl border-border/70 bg-white/5 px-3 text-white placeholder:text-text-dim focus-visible:border-brand-cyan/70 focus-visible:ring-brand-cyan/20";
const selectClass =
  "form-select flex h-11 w-full cursor-pointer rounded-xl border border-border/70 bg-white/5 px-3 text-sm text-white outline-none transition focus:border-brand-cyan/70";
const textAreaClass =
  "min-h-[128px] w-full rounded-2xl border border-border/70 bg-white/5 px-3 py-3 text-sm text-white placeholder:text-text-dim outline-none transition focus:border-brand-cyan/70";

function hasNetzplanResult(value: Partial<GridCheckResult> | null): value is GridCheckResult {
  return Boolean(
    value &&
      typeof value.score === "number" &&
      typeof value.machbarkeit_stufe === "string" &&
      typeof value.nvp_bezeichnung === "string" &&
      value.teil_scores &&
      value.kurzschluss &&
      value.projektprofil &&
      value.speicher_bewertung &&
      value.route_environment &&
      value.stakeholder_bewertung &&
      value.transparenz,
  );
}

function getVerdictLabel(stufe?: string) {
  if (stufe === "gruen") return "Machbar";
  if (stufe === "gelb") return "Bedingt machbar";
  if (stufe === "orange") return "Eingeschraenkt";
  if (stufe === "rot") return "Kritisch";
  return "Noch keine Analyse";
}

function formatProjectTypeLabel(value: string) {
  return PROJECT_TYPE_OPTIONS.find((option) => option.value === value)?.label ?? value;
}

function formatTimestamp(value?: string | null) {
  return value ? new Date(value).toLocaleString("de-DE") : "Noch nicht gespeichert";
}

export default function ProjectDetailWorkspace({ projectId: projectIdStr }: { projectId: string }) {
  const router = useRouter();
  const projectId = Number(projectIdStr);
  const [name, setName] = useState("");
  const [plz, setPlz] = useState("");
  const [typ, setTyp] = useState("pv");
  const [leistungKw, setLeistungKw] = useState("");
  const [description, setDescription] = useState("");
  const [profile, setProfile] = useState<ProjectRoleInputs>({});
  const [result, setResult] = useState<Partial<GridCheckResult> | null>(null);
  const [shareUserId, setShareUserId] = useState("");
  const [uiMessage, setUiMessage] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [isStartingCheckout, setIsStartingCheckout] = useState(false);
  const [paywallBilling, setPaywallBilling] = useState<BillingStatus | null>(null);
  const [selectedOfferId, setSelectedOfferId] = useState<string>("free");
  const [packageSelectionTouched, setPackageSelectionTouched] = useState(false);
  const queryClient = useQueryClient();

  const projectQuery = useQuery({
    queryKey: ["project", projectId],
    queryFn: () => getProject(projectId),
  });
  const billingQuery = useQuery<BillingStatus>({
    queryKey: ["billing-status"],
    queryFn: getBillingStatus,
  });

  const project = projectQuery.data;
  const analysisOptions: BillingAnalysisOption[] = billingQuery.data?.analysis_options ?? [];
  const selectedAnalysisOption =
    analysisOptions.find((option) => option.offer_id === selectedOfferId) ?? analysisOptions[0] ?? null;
  const effectiveBillingStatus = paywallBilling ?? billingQuery.data ?? null;
  const selectedPackageScope = selectedAnalysisOption?.package_scope ?? (selectedOfferId === "free" ? "basic" : undefined);
  const selectedPackageProfile = getOfferProfile(selectedAnalysisOption?.offer_id ?? selectedOfferId, selectedPackageScope);

  const updateMutation = useMutation({
    mutationFn: (payload: Parameters<typeof updateProject>[1]) => updateProject(projectId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] });
      queryClient.invalidateQueries({ queryKey: ["project", projectId] });
      setUiMessage("Projekt gespeichert.");
    },
    onError: () => setAnalysisError("Projekt konnte nicht gespeichert werden."),
  });

  const shareMutation = useMutation({
    mutationFn: (userId: number) => shareProject(projectId, userId, "viewer"),
    onSuccess: () => {
      setShareUserId("");
      setUiMessage("Projekt geteilt.");
    },
    onError: () => setAnalysisError("Projekt konnte nicht geteilt werden."),
  });

  useEffect(() => {
    if (projectQuery.isError) {
      router.replace("/login");
    }
  }, [projectQuery.isError, router]);

  useEffect(() => {
    if (!project) return;
    setName(project.name);
    setPlz(project.plz);
    setTyp(project.typ);
    setLeistungKw(String(project.leistung_kw));
    setDescription(project.description ?? "");
    setProfile(project.role_inputs ?? {});
    setResult(project.role_results ?? null);
  }, [project]);

  useEffect(() => {
    if (analysisOptions.length === 0) {
      setSelectedOfferId("free");
      setPackageSelectionTouched(false);
      return;
    }
    const preferred = analysisOptions.find((option) => option.default) ?? analysisOptions[0];
    const stillAvailable = analysisOptions.some((option) => option.offer_id === selectedOfferId);
    if (!packageSelectionTouched && preferred && preferred.offer_id !== selectedOfferId) {
      setSelectedOfferId(preferred.offer_id);
      return;
    }
    if (!stillAvailable && preferred) {
      setSelectedOfferId(preferred.offer_id);
      setPackageSelectionTouched(false);
    }
  }, [analysisOptions, packageSelectionTouched, selectedOfferId]);

  function analysisOptionLabel(option: BillingAnalysisOption) {
    if (option.offer_id === "free") {
      return `Free Check (${option.remaining_credits ?? 0} frei)`;
    }
    const creditText =
      option.remaining_credits === null || option.remaining_credits === undefined
        ? "laufend"
        : `${option.remaining_credits} Credit${option.remaining_credits === 1 ? "" : "s"}`;
    return `${option.label} (${creditText})`;
  }

  function normalizeRoleInputs(base: ProjectRoleInputs): ProjectRoleInputs {
    return {
      ...base,
      plz: base.plz ?? plz,
      antragsteller: base.antragsteller ?? name,
      anlagentyp:
        base.anlagentyp ??
        (typ === "pv"
          ? "solar"
          : typ === "wind"
            ? "wind"
            : typ === "bess" || typ === "battery"
              ? "batterie"
              : typ === "ladepark"
                ? "ladepark"
                : "sonstiges"),
      anschlussleistung_kw: base.anschlussleistung_kw ?? Number(leistungKw || 0),
    };
  }

  function buildProjectInput(): GridCheckInput {
    const normalizedProfile = normalizeRoleInputs(profile);
    const resolvedCustomerType = (
      normalizedProfile.kundentyp ?? normalizedProfile.stakeholder_context?.customer_type
    ) as StakeholderContextInput["customer_type"] | undefined;
    return {
      plz: normalizedProfile.plz ?? plz,
      ort: normalizedProfile.ort,
      anlagentyp:
        normalizedProfile.anlagentyp ??
        (typ === "pv"
          ? "solar"
          : typ === "wind"
            ? "wind"
            : typ === "bess" || typ === "battery"
              ? "batterie"
              : typ === "ladepark"
                ? "ladepark"
                : "sonstiges"),
      richtung: normalizedProfile.richtung ?? "einspeisung",
      anschlussleistung_kw: normalizedProfile.anschlussleistung_kw ?? Number(leistungKw || 0),
      cos_phi: normalizedProfile.cos_phi ?? 0.95,
      spannungsebene: normalizedProfile.spannungsebene ?? "MS",
      topologie: normalizedProfile.topologie ?? "unbekannt",
      entfernung_km: normalizedProfile.entfernung_km,
      kabeltyp: normalizedProfile.kabeltyp,
      sk_min_mva: normalizedProfile.sk_min_mva,
      sk_max_mva: normalizedProfile.sk_max_mva,
      rx_verhaeltnis: normalizedProfile.rx_verhaeltnis,
      trafo_sr_kva: normalizedProfile.trafo_sr_kva,
      trafo_uk_pct: normalizedProfile.trafo_uk_pct,
      trafo_anzahl: normalizedProfile.trafo_anzahl,
      vorbelastung_pct: normalizedProfile.vorbelastung_pct,
      netzkapazitaet_kw: normalizedProfile.netzkapazitaet_kw,
      projektreife: normalizedProfile.projektreife,
      baugenehmigung_vorhanden: normalizedProfile.baugenehmigung_vorhanden,
      foerderfrist: normalizedProfile.foerderfrist,
      antragsteller: normalizedProfile.antragsteller ?? name,
      project_components: normalizedProfile.project_components,
      netzanschlusspunkt: normalizedProfile.netzanschlusspunkt,
      storage_profile: normalizedProfile.storage_profile,
      environmental_route: normalizedProfile.environmental_route,
      project_location: normalizedProfile.project_location,
      stakeholder_context: {
        ...(normalizedProfile.stakeholder_context ?? {}),
        customer_type: resolvedCustomerType,
        investor_relevant:
          (normalizedProfile.stakeholder_context?.investor_relevant ?? false) || resolvedCustomerType === "investor",
      },
    };
  }

  const projectInput = buildProjectInput();
  const selectedPackageWarnings = getPackageBoundaryWarnings(projectInput, selectedPackageScope);
  const projectStakeholderPath = resolveStakeholderProductPath({
    kundentyp: profile.kundentyp,
    stakeholder_context: projectInput.stakeholder_context,
  });
  const stakeholderCopy = getStakeholderProductCopy(projectStakeholderPath);
  const showDeepTechnicalDetails = canViewDeepTechnicalDetails(projectStakeholderPath);
  const projectCostBand = buildIndicativeCostBand(result);
  const projektiererGuidance = buildProjektiererGuidance(result);
  const siteMarkerHref = buildSiteMarkerHref({
    source: "project",
    projectId,
    projectName: name || project?.name,
    plz: projectInput.plz,
    ort: projectInput.ort,
    latitude: projectInput.project_location?.latitude,
    longitude: projectInput.project_location?.longitude,
    returnTo: `/projects/${projectId}`,
  });
  const canRunAnalysis = billingQuery.data?.can_run_analysis !== false;
  const shareUserIdTrimmed = shareUserId.trim();
  const shareUserIdIsValid = shareUserIdTrimmed.length === 0 || /^\d+$/.test(shareUserIdTrimmed);

  const liveProject = useMemo<Project | null>(() => {
    if (!project) return null;
    return {
      ...project,
      name: name || project.name,
      plz: plz || project.plz,
      typ: typ || project.typ,
      leistung_kw: Number(leistungKw || project.leistung_kw || 0),
      description: description || project.description || undefined,
      role_inputs: profile,
      role_results: (result ?? project.role_results ?? {}) as Partial<GridCheckResult>,
    };
  }, [description, leistungKw, name, plz, profile, project, result, typ]);

  const insight = liveProject ? getProjectCommercialInsight(liveProject) : null;

  async function onSave(event: FormEvent) {
    event.preventDefault();
    setUiMessage(null);
    setAnalysisError(null);
    const normalizedProfile = normalizeRoleInputs(profile);
    setProfile(normalizedProfile);
    await updateMutation.mutateAsync({
      name,
      plz,
      typ,
      leistung_kw: Number(leistungKw),
      description,
      role_inputs: normalizedProfile,
    });
  }

  async function onShare(event: FormEvent) {
    event.preventDefault();
    setUiMessage(null);
    if (!shareUserIdTrimmed) return;
    if (!shareUserIdIsValid) {
      setAnalysisError("Bitte fuer die Projektfreigabe eine numerische User-ID eingeben.");
      return;
    }
    setAnalysisError(null);
    await shareMutation.mutateAsync(Number(shareUserIdTrimmed));
  }

  async function onAnalyzeFromProject() {
    setIsAnalyzing(true);
    setUiMessage(null);
    setAnalysisError(null);
    setPaywallBilling(null);
    try {
      const analysisResult = await analyzeGridcheck(buildProjectInput(), {
        requestedOfferId: selectedOfferId === "free" ? "free" : selectedOfferId,
      });
      setResult(analysisResult);
      pushCompareSnapshot(projectIdStr, analysisResult);
      const normalizedProfile = normalizeRoleInputs(profile);
      setProfile(normalizedProfile);
      try {
        await updateMutation.mutateAsync({
          name,
          plz,
          typ,
          leistung_kw: Number(leistungKw),
          description,
          role_inputs: normalizedProfile,
          role_results: analysisResult,
        });
      } catch {
        setAnalysisError("Analyse wurde berechnet, konnte aber nicht im Projekt gespeichert werden.");
        return;
      }
      setUiMessage("Projektanalyse aktualisiert.");
      await queryClient.invalidateQueries({ queryKey: ["billing-status"] });
    } catch (err) {
      if (err instanceof AnalyzeApiError) {
        setAnalysisError(err.message);
        if (err.status === 402) {
          setPaywallBilling(err.detail?.billing ?? null);
          await queryClient.invalidateQueries({ queryKey: ["billing-status"] });
        }
      } else {
        setAnalysisError("Projektanalyse konnte nicht gestartet werden.");
      }
    } finally {
      setIsAnalyzing(false);
    }
  }

  async function onExportPdf() {
    if (!result) {
      setAnalysisError("Bitte zuerst eine Analyse durchfuehren, bevor der PDF-Report exportiert wird.");
      return;
    }
    setIsExporting(true);
    setAnalysisError(null);
    setPaywallBilling(null);
    try {
      const stakeholder = projectStakeholderPath;
      const exportScope = selectedAnalysisOption?.report_scope ?? selectedPackageScope ?? "report";
      const { blob, filename } = await exportStakeholderPdf(buildProjectInput(), stakeholder, {
        requestedOfferId: selectedOfferId === "free" ? "free" : selectedOfferId,
        analysisRunId: result.history?.analysis_run_id,
      });
      downloadBlobFile(
        blob,
        filename || `project-${projectId}-${stakeholder}-${exportScope}.pdf`,
      );
    } catch (err) {
      if (err instanceof AnalyzeApiError) {
        setAnalysisError(err.message);
        if (err.status === 401) {
          await queryClient.invalidateQueries({ queryKey: ["auth-me"] });
        }
      } else {
        setAnalysisError("Projekt-Report konnte nicht exportiert werden. Bitte erneut versuchen.");
      }
    } finally {
      setIsExporting(false);
    }
  }

  async function handleUpgradeCheckout(offerId = "pro_lizenz") {
    if (isStartingCheckout) return;
    setIsStartingCheckout(true);
    setAnalysisError(null);
    try {
      const session = await createBillingCheckout(offerId);
      window.location.assign(session.url);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : "Upgrade konnte nicht gestartet werden.");
      setIsStartingCheckout(false);
    }
  }

  return (
    <main className="min-h-screen bg-bg text-white">
      <Header />
      <div className="mx-auto max-w-6xl px-4 py-6 sm:px-6 sm:py-8">
        <section className="flex flex-col gap-4 border-b border-border/70 pb-6">
          <Link href="/projects" className="inline-flex items-center gap-2 text-sm text-text-muted transition hover:text-white">
            <ArrowLeft className="h-4 w-4" />
            Zur Projektliste
          </Link>
          <div className="grid gap-5 xl:grid-cols-[minmax(0,1.15fr)_minmax(320px,0.85fr)]">
            <div>
              <div className="flex flex-wrap gap-2">
                <span className="rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-medium text-brand-cyan">
                  #{projectId}
                </span>
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white">
                  {formatProjectTypeLabel(typ || project?.typ || "pv")}
                </span>
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white">
                  {leistungKw || project?.leistung_kw || "0"} kW
                </span>
                <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-white">
                  {getVerdictLabel(typeof result?.machbarkeit_stufe === "string" ? result.machbarkeit_stufe : undefined)}
                </span>
              </div>
              <h1 className="mt-4 text-3xl font-semibold text-white sm:text-4xl">{name || project?.name || `Projekt ${projectId}`}</h1>
              <p className="mt-4 max-w-3xl text-sm leading-7 text-text-muted">
                {insight?.summary ??
                  "Projektkontext, Analyse, Paketwahl und Vor-Ort-Marker laufen hier in einem gemeinsamen MVP-Workspace zusammen."}
              </p>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-white/85">
                {insight ? `Naechster Schritt: ${insight.nextStep}` : "Projekt speichern, Analyse starten und danach bei Bedarf mobil Marker dokumentieren."}
              </p>
              <p className="mt-3 max-w-3xl text-sm leading-7 text-text-muted">
                {stakeholderCopy.visibilityNote}
              </p>
              <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
                <Button
                  type="button"
                  onClick={onAnalyzeFromProject}
                  disabled={isAnalyzing || !canRunAnalysis}
                  className="h-11 rounded-xl bg-brand-orange px-5 text-white hover:bg-brand-orangeHover"
                >
                  <Radar className="mr-2 h-4 w-4" />
                  {isAnalyzing ? "Analyse laeuft..." : "Analyse starten"}
                </Button>
                <Button
                  type="button"
                  onClick={onExportPdf}
                  disabled={!result || isExporting}
                  className="h-11 rounded-xl bg-brand-cyan px-5 text-black hover:bg-brand-cyan/90 disabled:opacity-60"
                >
                  <FileDown className="mr-2 h-4 w-4" />
                  {isExporting ? "Export laeuft..." : stakeholderCopy.exportLabel}
                </Button>
                <Link
                  href={siteMarkerHref}
                  className="inline-flex h-11 items-center justify-center rounded-xl border border-white/15 bg-white/5 px-5 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  <MapPinned className="mr-2 h-4 w-4" />
                  Vor-Ort-Marker aufnehmen
                </Link>
                <Link
                  href={`/projects/${projectIdStr}/szenarien-vergleich`}
                  className="inline-flex h-11 items-center justify-center rounded-xl border border-white/15 bg-white/5 px-5 text-sm font-semibold text-white transition hover:bg-white/10"
                >
                  <GitCompareArrows className="mr-2 h-4 w-4" />
                  Szenarien vergleichen
                </Link>
              </div>
            </div>

            <div className="rounded-[28px] border border-white/10 bg-white/5 p-5">
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Score</div>
                  <div className="mt-2 text-2xl font-semibold text-white">
                    {typeof result?.score === "number" ? `${result.score}/100` : "Noch offen"}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Rollenpfad</div>
                  <div className="mt-2 text-sm font-semibold text-white">{stakeholderCopy.label}</div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Paketpfad</div>
                  <div className="mt-2 text-sm font-semibold text-white">
                    {result?.billing_access
                      ? getOfferProfile(result.billing_access.offer_id, result.billing_access.package_scope).title
                      : "Noch kein Paket-Run"}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Standortkontext</div>
                  <div className="mt-2 text-sm font-semibold text-white">
                    {projectInput.project_location?.address_hint || "Noch keine Praezisierung"}
                  </div>
                </div>
                <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Zuletzt aktualisiert</div>
                  <div className="mt-2 text-sm font-semibold text-white">
                    {formatTimestamp(project?.updated_at ?? project?.created_at)}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {uiMessage ? (
          <div className="mt-6 rounded-2xl border border-brand-cyan/30 bg-brand-cyan/10 px-4 py-3 text-sm text-brand-cyan">
            {uiMessage}
          </div>
        ) : null}
        {analysisError ? (
          <div className="mt-6 rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-300">
            {analysisError}
          </div>
        ) : null}
        {isAnalyzing ? <AnalysisProgressPanel active className="mt-6" /> : null}
        {effectiveBillingStatus?.upgrade_required && effectiveBillingStatus.subscription_state !== "checkout_pending" ? (
          <div className="mt-6">
            <BillingUpgradePrompt
              billing={effectiveBillingStatus}
              onCheckout={handleUpgradeCheckout}
              isStartingCheckout={isStartingCheckout}
              compact
            />
          </div>
        ) : null}

        <div className="mt-6 grid gap-6 xl:grid-cols-[minmax(0,1.35fr)_minmax(320px,0.8fr)]">
          <div className="space-y-6">
            <form onSubmit={onSave} className="space-y-6">
              <Card className={cardClass}>
                <CardHeader className="gap-3">
                  <div className="flex items-center gap-3">
                    <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-brand-cyan">
                      <ClipboardList className="h-5 w-5" />
                    </div>
                    <div>
                      <CardTitle className="text-white">Projektrahmen</CardTitle>
                      <CardDescription className="text-text-muted">
                        Stammdaten, Kurzbeschreibung und das aktive Analysepaket.
                      </CardDescription>
                    </div>
                  </div>
                </CardHeader>
                <CardContent className="space-y-5">
                  <div className="grid gap-4 md:grid-cols-2">
                    <div className="space-y-2 md:col-span-2">
                      <label htmlFor="project-name" className="text-sm font-medium text-white">
                        Projektname
                      </label>
                      <Input
                        id="project-name"
                        className={fieldClass}
                        value={name}
                        onChange={(event) => setName(event.target.value)}
                        placeholder="Projektname"
                      />
                    </div>
                    <div className="space-y-2">
                      <label htmlFor="project-plz" className="text-sm font-medium text-white">
                        PLZ
                      </label>
                      <Input
                        id="project-plz"
                        className={fieldClass}
                        value={plz}
                        onChange={(event) => setPlz(event.target.value)}
                        placeholder="PLZ"
                        maxLength={5}
                        inputMode="numeric"
                      />
                    </div>
                    <div className="space-y-2">
                      <label htmlFor="project-type" className="text-sm font-medium text-white">
                        Projekttyp
                      </label>
                      <select
                        id="project-type"
                        className={selectClass}
                        value={typ}
                        onChange={(event) => setTyp(event.target.value)}
                      >
                        {PROJECT_TYPE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value} className="bg-bg text-white">
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="space-y-2">
                      <label htmlFor="project-power" className="text-sm font-medium text-white">
                        Leistung in kW
                      </label>
                      <Input
                        id="project-power"
                        className={fieldClass}
                        value={leistungKw}
                        onChange={(event) => setLeistungKw(event.target.value)}
                        placeholder="Leistung kW"
                        inputMode="decimal"
                      />
                    </div>
                    <div className="space-y-2 md:col-span-2">
                      <label htmlFor="project-description" className="text-sm font-medium text-white">
                        Kurzbeschreibung
                      </label>
                      <textarea
                        id="project-description"
                        className={textAreaClass}
                        rows={5}
                        value={description}
                        onChange={(event) => setDescription(event.target.value)}
                        placeholder="Worum geht es in diesem Projekt, welche Rahmenbedingungen oder Risiken sind schon sichtbar?"
                      />
                    </div>
                  </div>

                  {analysisOptions.length > 0 ? (
                    <div className="rounded-[22px] border border-white/10 bg-black/10 p-4">
                      <p className="text-sm font-semibold text-white">Paket fuer die naechste Projektanalyse</p>
                      <div className="mt-4 grid gap-3 md:grid-cols-2">
                        {analysisOptions.map((option) => {
                          const isSelected = selectedOfferId === option.offer_id;
                          return (
                            <button
                              key={option.offer_id}
                              type="button"
                              onClick={() => {
                                setSelectedOfferId(option.offer_id);
                                setPackageSelectionTouched(true);
                              }}
                              className={`rounded-2xl border p-4 text-left transition ${
                                isSelected
                                  ? "border-brand-cyan/30 bg-brand-cyan/10"
                                  : "border-white/10 bg-white/5 hover:bg-white/10"
                              }`}
                            >
                              <p className="text-sm font-semibold text-white">{analysisOptionLabel(option)}</p>
                              <p className="mt-1 text-xs text-text-muted">
                                Scope {option.package_scope} · {getReportScopeLabel(option.report_scope)}
                              </p>
                            </button>
                          );
                        })}
                      </div>
                      <div className="mt-4 rounded-xl border border-white/10 bg-white/5 p-3 text-xs leading-5 text-text-muted">
                        {selectedPackageProfile.title} · {getPackageScopeLabel(selectedPackageScope)} ·{" "}
                        {getReportScopeLabel(selectedAnalysisOption?.report_scope)}
                      </div>
                      {selectedPackageWarnings.length > 0 ? (
                        <div className="mt-4 rounded-xl border border-amber-400/30 bg-amber-500/10 p-3">
                          <p className="text-sm font-semibold text-amber-100">Hinweis zur Paketgrenze</p>
                          <ul className="mt-2 space-y-1 text-xs leading-5 text-amber-100/90">
                            {selectedPackageWarnings.map((warning) => (
                              <li key={warning}>{warning}</li>
                            ))}
                          </ul>
                        </div>
                      ) : null}
                    </div>
                  ) : null}

                  <div className="flex flex-col-reverse gap-3 sm:flex-row sm:justify-between">
                    <p className="text-sm text-text-muted">
                      Aenderungen an Stammdaten und Profil bleiben im Projektkontext nachvollziehbar.
                    </p>
                    <Button
                      type="submit"
                      disabled={updateMutation.isPending}
                      className="h-11 rounded-xl bg-brand-orange px-5 text-white hover:bg-brand-orangeHover"
                    >
                      {updateMutation.isPending ? "Speichert..." : "Projekt speichern"}
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <ProjectProfileFields value={profile} onChange={setProfile} compact />
            </form>

            {result ? <AnalysisDisclaimer className="mb-6" /> : null}

            {result && hasNetzplanResult(result) && showDeepTechnicalDetails ? (
              <NetzplanVisualization
                input={projectInput}
                result={result}
                meta={{
                  kundentyp: profile.kundentyp,
                  projektname: name,
                  ort: profile.ort,
                  erzeugungstyp: typ,
                }}
              />
            ) : null}
            {result && hasNetzplanResult(result) && !showDeepTechnicalDetails ? (
              <Card className={cardClass}>
                <CardHeader>
                  <CardTitle className="text-white">Sichtbarkeitsgrenze</CardTitle>
                  <CardDescription className="text-text-muted">
                    Dieser Rollenpfad zeigt bewusst keine tiefen internen Netz- oder Impedanzdetails.
                  </CardDescription>
                </CardHeader>
                <CardContent className="text-sm leading-7 text-text-muted">
                  {stakeholderCopy.visibilityNote} Die Projektansicht bleibt in diesem Pfad auf Standortqualitaet,
                  Risiko, Kostenbandbreite und revisionssichere Verdichtung fokussiert.
                </CardContent>
              </Card>
            ) : null}
          </div>

          <div className="space-y-6">
            <Card className={cardClass}>
              <CardHeader>
                <CardTitle className="text-white">Analyse-Stand</CardTitle>
                <CardDescription className="text-text-muted">
                  Ergebnis, Nutzerverstaendlichkeit und naechste Schritte auf einen Blick.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Verdict</div>
                  <p className="mt-2 text-lg font-semibold text-white">
                    {getVerdictLabel(typeof result?.machbarkeit_stufe === "string" ? result.machbarkeit_stufe : undefined)}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-text-muted">
                    {result
                      ? result.spannungsbewertung || result.n1_hinweis || "Analyse gespeichert."
                      : "Noch kein gespeicherter Run. Das Projekt wartet auf die erste belastbare Analyse."}
                  </p>
                </div>

                {result?.empfehlungen?.length ? (
                  <ul className="space-y-2 text-sm leading-6 text-text-muted">
                    {result.empfehlungen.slice(0, 4).map((item) => (
                      <li key={item} className="flex gap-2">
                        <span className="text-brand-cyan">•</span>
                        <span>{item}</span>
                      </li>
                    ))}
                  </ul>
                ) : null}

                <div className="grid gap-3 sm:grid-cols-2">
                  <div className="rounded-xl border border-white/10 bg-black/10 p-3">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Audit</div>
                    <p className="mt-2 text-sm font-semibold text-white">{result?.revision?.hash ?? "Noch offen"}</p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-black/10 p-3">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Letzter Run</div>
                    <p className="mt-2 text-sm font-semibold text-white">
                      {result?.history?.analysis_run_id ? `Run #${result.history.analysis_run_id}` : "Noch keiner"}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className={cardClass}>
              <CardHeader>
                <CardTitle className="text-white">{stakeholderCopy.label}: Arbeitsmodus</CardTitle>
                <CardDescription className="text-text-muted">
                  Rollenbezogene Projektfuehrung, Sichtbarkeit und naechste Schritte fuer diesen Workspace.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-sm leading-6 text-text-muted">
                <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
                  <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">MVP-Fokus</div>
                  <p className="mt-2 text-white">{stakeholderCopy.summaryLead}</p>
                </div>
                {projectStakeholderPath === "invest" ? (
                  <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Kostenband / Due Diligence</div>
                    <div className="mt-2 space-y-1 text-white">
                      <p>Basiswert: {projectCostBand ? `${projectCostBand.basis.toLocaleString("de-DE")} EUR` : "Noch offen"}</p>
                      <p className="text-text-muted">
                        Risiken: {projectCostBand?.drivers?.length ? projectCostBand.drivers.join(" · ") : "Werden nach dem ersten Run verdichtet."}
                      </p>
                    </div>
                  </div>
                ) : null}
                {projectStakeholderPath === "vnb" ? (
                  <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Vorpruefung / Audit</div>
                    <div className="mt-2 space-y-1 text-white">
                      <p>N-1-Nachweistiefe: {result?.n1?.n1_klasse ?? "Noch offen"}</p>
                      <p className="text-text-muted">Audit-Hash: {result?.revision?.hash ?? "Wird nach dem ersten Run gesetzt."}</p>
                    </div>
                  </div>
                ) : null}
                {projectStakeholderPath === "projektierer" ? (
                  <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                    <div className="text-[11px] uppercase tracking-[0.18em] text-text-dim">Projektierer-Naechste Schritte</div>
                    <ul className="mt-2 space-y-2">
                      {projektiererGuidance.compareAxes.slice(0, 3).map((item) => (
                        <li key={item} className="flex gap-2">
                          <span className="text-brand-cyan">•</span>
                          <span>{item}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : null}
                <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-amber-100">
                  {stakeholderCopy.visibilityNote}
                </div>
              </CardContent>
            </Card>

            {result ? (
              <ProductDecisionGuide
                title="Naechster Produktpfad fuer dieses Projekt"
                description="Die Entscheidungshilfe macht sichtbar, ob dieses Projekt im Self-Serve-Pfad bleibt oder bewusst in Richtung Professional, Express oder Pilot wechselt."
                currentOfferId={result.billing_access?.offer_id}
                currentPackageScope={result.billing_access?.package_scope}
                compact
              />
            ) : null}

            <Card className={cardClass}>
              <CardHeader>
                <CardTitle className="text-white">Projekt teilen</CardTitle>
                <CardDescription className="text-text-muted">
                  Viewer-Freigabe fuer andere Nutzer. Die User-ID bleibt bewusst explizit.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={onShare} className="space-y-4">
                  <div className="space-y-2">
                    <label htmlFor="share-user-id" className="text-sm font-medium text-white">
                      Ziel-User-ID
                    </label>
                    <Input
                      id="share-user-id"
                      className={fieldClass}
                      placeholder="Numerische User-ID"
                      value={shareUserId}
                      onChange={(event) => setShareUserId(event.target.value)}
                      inputMode="numeric"
                    />
                  </div>
                  <Button
                    type="submit"
                    disabled={shareMutation.isPending || !shareUserIdTrimmed || !shareUserIdIsValid}
                    className="h-11 rounded-xl bg-brand-mint px-5 text-black hover:bg-brand-mint/90"
                  >
                    <Share2 className="mr-2 h-4 w-4" />
                    {shareMutation.isPending ? "Teilt..." : "Projekt teilen"}
                  </Button>
                </form>
              </CardContent>
            </Card>

            <Card className={cardClass}>
              <CardHeader>
                <CardTitle className="text-white">Workspace-Navigation</CardTitle>
                <CardDescription className="text-text-muted">
                  Marker, Settings und weitere Folgepfade fuer diesen Projektkontext.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Link
                  href={siteMarkerHref}
                  className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/10"
                >
                  <span>Vor-Ort-Marker fuer dieses Projekt</span>
                  <MapPinned className="h-4 w-4 text-brand-cyan" />
                </Link>
                <Link
                  href="/settings"
                  className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/10"
                >
                  <span>Tarife, Credits und Analyse-History</span>
                  <Settings2 className="h-4 w-4 text-brand-cyan" />
                </Link>
                <Link
                  href={projectStakeholderPath === "vnb" ? "/vnb" : projectStakeholderPath === "invest" ? "/invest" : "/projektierer"}
                  className="flex items-center justify-between rounded-2xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-medium text-white transition hover:bg-white/10"
                >
                  <span>Zum {stakeholderCopy.label}-Rollenpfad</span>
                  <Radar className="h-4 w-4 text-brand-cyan" />
                </Link>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </main>
  );
}


