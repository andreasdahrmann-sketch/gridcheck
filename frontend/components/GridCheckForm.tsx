"use client";
import Link from "next/link";
import { useEffect, useState } from "react";
import type {
  GridCheckInput,
  GridCheckResult,
  Spannungsebene,
  StakeholderContextInput,
  Topologie,
} from "../types";
import VnbBanner from "./VnbBanner";
import { AnalysisDisclaimer } from "@/components/legal/AnalysisDisclaimer";
import NetzplanVisualization from "./NetzplanVisualization";
import BillingUpgradePrompt from "./BillingUpgradePrompt";
import AnalysisProgressPanel from "@/components/analysis/AnalysisProgressPanel";
import ProductDecisionGuide from "./billing/ProductDecisionGuide";
import N1AssessmentPanel from "./N1AssessmentPanel";
import { analyzeGridcheck, AnalyzeApiError, exportStakeholderPdf } from "../lib/api/analyze";
import { downloadBlobFile } from "../lib/download-blob";
import ProjectProfileFields from "./ProjectProfileFields";
import { submitKiFeedback } from "../lib/api/ki";
import { me, type AuthUser } from "@/lib/api/auth";
import {
  createBillingCheckout,
  getBillingStatus,
  type BillingAnalysisOption,
  type BillingOffer,
  type BillingStatus,
} from "@/lib/api/billing";
import {
  getOfferProfile,
  getPackageBoundaryWarnings,
  getPackageScopeLabel,
  getReportScopeLabel,
} from "@/lib/billing-product";
import {
  buildIndicativeCostBand,
  buildProjektiererGuidance,
  canViewDeepTechnicalDetails,
  getStakeholderProductCopy,
  resolveStakeholderProductPath,
} from "@/lib/stakeholder-product";
import { buildSiteMarkerHref } from "@/lib/app-flow";
import {
  estimateCableLength,
  formatConnectionType,
  getPowerLimitHints,
  hasNetzplanResult,
  resolveCosPhiDefault,
} from "@/lib/gridcheck-engine";
import { readUserPreferences } from "@/lib/user-preferences";
import DemoCaseLoader, { type DemoCase } from "./DemoCaseLoader";
import DemoModeBanner from "./DemoModeBanner";

type CustomerType = "projektierer" | "speicherbetreiber" | "netzbetreiber" | "investor";

const CUSTOMER_LABELS: Record<CustomerType, string> = {
  projektierer: "Projektierer / EPC",
  speicherbetreiber: "Speicher- / Parkbetreiber",
  netzbetreiber: "Netzbetreiber",
  investor: "Investor / Finanzierung",
};

const CUSTOMER_DESC: Record<CustomerType, string> = {
  projektierer: "Prüfung ob Netzanschluss technisch machbar ist.",
  speicherbetreiber: "Bewertung inkl. Speicherdimensionierung.",
  netzbetreiber: "N-1 Analyse, Engpasserkennung, Kapazitätsbewertung.",
  investor: "Standort-, Risiko- und Kostenbandbreite fuer Invest- und DD-Entscheidungen.",
};

const ERZEUGUNGS_OPTIONEN: Record<CustomerType, string[]> = {
  projektierer: ["PV", "Wind", "PV + Speicher", "Wind + Speicher", "Hybridpark"],
  speicherbetreiber: ["BESS", "PV + Speicher", "Wind + Speicher", "Hybridpark"],
  netzbetreiber: ["Alle Einspeiser", "PV-Park", "Windpark", "BESS", "Mischgebiet"],
  investor: ["PV", "Wind", "BESS", "Hybridpark", "Portfolio-Cluster"],
};

interface MetaData {
  kundentyp: CustomerType | "";
  projektname: string;
  ort: string;
  erzeugungstyp: string;
}

type GridCheckDraft = {
  input: GridCheckInput;
  meta: MetaData;
  step: number;
};

type GridCheckFormProps = {
  forcedCustomerType?: CustomerType;
};

const INITIAL_INPUT: GridCheckInput = {
  anlagentyp: "solar" as const,
  anschlussleistung_kw: 5000,
  spannungsebene: "MS" as Spannungsebene,
  cos_phi: 0.95,
  richtung: "einspeisung",
  plz: "30159",
  topologie: "unbekannt" as Topologie,
};

const INITIAL_META: MetaData = {
  kundentyp: "",
  projektname: "",
  ort: "",
  erzeugungstyp: "",
};

const DRAFT_STORAGE_KEY = "gridcheck_check_form_draft";

function createAnalysisRunId() {
  return `GC-${Date.now().toString(36).toUpperCase()}`;
}

export default function GridCheckForm({ forcedCustomerType }: GridCheckFormProps) {
  const [step, setStep] = useState(forcedCustomerType ? 1 : 0);
  const [input, setInput] = useState<GridCheckInput>({ ...INITIAL_INPUT });
  const [meta, setMeta] = useState<MetaData>({
    ...INITIAL_META,
    kundentyp: forcedCustomerType ?? "",
  });
  const [result, setResult] = useState<GridCheckResult | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);
  const [draftReady, setDraftReady] = useState(false);
  const [analysisRunId, setAnalysisRunId] = useState(() => createAnalysisRunId());
  const [feedbackType, setFeedbackType] = useState<"bestaetigt" | "korrigiert">("bestaetigt");
  const [feedbackDecision, setFeedbackDecision] = useState<"A" | "B" | "C">("B");
  const [feedbackComment, setFeedbackComment] = useState("");
  const [feedbackMessage, setFeedbackMessage] = useState<string | null>(null);
  const [isSubmittingFeedback, setIsSubmittingFeedback] = useState(false);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [paywallBilling, setPaywallBilling] = useState<BillingStatus | null>(null);
  const [isBillingLoading, setIsBillingLoading] = useState(true);
  const [isStartingCheckout, setIsStartingCheckout] = useState(false);
  const [selectedOfferId, setSelectedOfferId] = useState<string>("free");
  const [packageSelectionTouched, setPackageSelectionTouched] = useState(false);
  const [activeDemoId, setActiveDemoId] = useState<string | null>(null);

  const ct = meta.kundentyp as CustomerType;
  const stakeholderPath = resolveStakeholderProductPath({
    kundentyp: meta.kundentyp,
    stakeholder_context: input.stakeholder_context,
  });
  const stakeholderCopy = getStakeholderProductCopy(stakeholderPath);
  const showDeepTechnicalDetails = canViewDeepTechnicalDetails(stakeholderPath);
  const powerLimitHints = getPowerLimitHints(input.spannungsebene, input.anschlussleistung_kw);
  const cableLengthHint = estimateCableLength(input);
  const cosPhiHint = resolveCosPhiDefault(input);

  const updateInput = (patch: Partial<GridCheckInput>) => setInput(prev => ({ ...prev, ...patch }));
  const updateMeta = (patch: Partial<MetaData>) => setMeta(prev => ({ ...prev, ...patch }));

  const applyDemoCase = (demo: DemoCase) => {
    const demoCustomerType = demo.kundentyp as CustomerType;
    setInput((prev) => ({ ...INITIAL_INPUT, ...prev, ...demo.input }));
    setMeta((prev) => ({
      ...prev,
      kundentyp: forcedCustomerType ?? demoCustomerType ?? prev.kundentyp,
      ort: demo.input.ort ?? prev.ort,
      projektname: prev.projektname || demo.label.replace("[DEMO] ", "").trim(),
      erzeugungstyp:
        prev.erzeugungstyp ||
        (demo.input.anlagentyp === "batterie" ? "BESS" : demo.input.anlagentyp === "solar" ? "PV" : ""),
    }));
    setActiveDemoId(demo.id);
    setResult(null);
    setAnalysisError(null);
    if (!forcedCustomerType && demoCustomerType) {
      setStep(1);
    }
  };

  const buildCombinedInput = (): GridCheckInput => ({
    ...input,
    ort: meta.ort || input.ort,
    antragsteller: meta.projektname || input.antragsteller,
    stakeholder_context: {
      ...(input.stakeholder_context ?? {}),
      customer_type: (meta.kundentyp || input.stakeholder_context?.customer_type) as
        | StakeholderContextInput["customer_type"]
        | undefined,
      investor_relevant:
        (input.stakeholder_context?.investor_relevant ?? false) ||
        meta.kundentyp === "investor",
    },
  });

  useEffect(() => {
    const preferences = readUserPreferences();

    if (preferences.persistCheckDraft) {
      try {
        const rawDraft = window.localStorage.getItem(DRAFT_STORAGE_KEY);
        if (rawDraft) {
          const parsedDraft = JSON.parse(rawDraft) as Partial<GridCheckDraft>;
          if (parsedDraft.input) {
            setInput({ ...INITIAL_INPUT, ...parsedDraft.input });
          }
          if (parsedDraft.meta) {
            setMeta({
              ...INITIAL_META,
              ...parsedDraft.meta,
              kundentyp: forcedCustomerType ?? parsedDraft.meta.kundentyp ?? "",
            });
          } else if (forcedCustomerType || preferences.defaultCustomerType) {
            setMeta((current) => ({
              ...current,
              kundentyp: forcedCustomerType ?? preferences.defaultCustomerType ?? current.kundentyp,
            }));
          }
          if (typeof parsedDraft.step === "number" && parsedDraft.step >= 0 && parsedDraft.step <= 1) {
            setStep(forcedCustomerType ? 1 : parsedDraft.step);
          }
          setDraftReady(true);
          return;
        }
      } catch {
        window.localStorage.removeItem(DRAFT_STORAGE_KEY);
      }
    }

    if (forcedCustomerType || preferences.defaultCustomerType) {
      setMeta((current) => ({
        ...current,
        kundentyp: forcedCustomerType ?? current.kundentyp ?? preferences.defaultCustomerType ?? "",
      }));
    }
    setDraftReady(true);
  }, [forcedCustomerType]);

  useEffect(() => {
    if (!forcedCustomerType) {
      return;
    }

    setMeta((current) => (current.kundentyp === forcedCustomerType ? current : { ...current, kundentyp: forcedCustomerType }));
    setStep((current) => (current === 0 ? 1 : current));
  }, [forcedCustomerType]);

  useEffect(() => {
    if (!draftReady) return;

    const preferences = readUserPreferences();
    if (!preferences.persistCheckDraft) {
      window.localStorage.removeItem(DRAFT_STORAGE_KEY);
      return;
    }

    if (step > 1) {
      return;
    }

    const draft: GridCheckDraft = {
      input,
      meta,
      step,
    };
    window.localStorage.setItem(DRAFT_STORAGE_KEY, JSON.stringify(draft));
  }, [draftReady, input, meta, step]);

  useEffect(() => {
    let active = true;

    async function loadAccessState() {
      try {
        const user = await me();
        if (!active) return;
        setAuthUser(user);
        const billing = await getBillingStatus();
        if (!active) return;
        setBillingStatus(billing);
      } catch {
        if (!active) return;
        setAuthUser(null);
        setBillingStatus(null);
      } finally {
        if (active) {
          setIsBillingLoading(false);
        }
      }
    }

    void loadAccessState();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    if (!billingStatus) return;
    const options = billingStatus.analysis_options ?? [];
    if (options.length === 0) {
      setSelectedOfferId("free");
      setPackageSelectionTouched(false);
      return;
    }
    const preferred = options.find((option) => option.default) ?? options[0];
    const stillAvailable = options.some((option) => option.offer_id === selectedOfferId);
    if (!packageSelectionTouched && preferred && preferred.offer_id !== selectedOfferId) {
      setSelectedOfferId(preferred.offer_id);
      return;
    }
    if (!stillAvailable && preferred) {
      setSelectedOfferId(preferred.offer_id);
      setPackageSelectionTouched(false);
    }
  }, [billingStatus, packageSelectionTouched, selectedOfferId]);

  const refreshBillingStatus = async () => {
    if (!authUser) return;
    try {
      const next = await getBillingStatus();
      setBillingStatus(next);
      setPaywallBilling(next.upgrade_required ? next : null);
    } catch {
      // Ignore transient refresh errors and keep the last known UI state.
    }
  };

  const handleUpgradeCheckout = async (offerId = "pro_lizenz") => {
    if (isStartingCheckout) return;
    setIsStartingCheckout(true);
    setAnalysisError(null);
    try {
      const session = await createBillingCheckout(offerId);
      window.location.href = session.url;
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : "Upgrade konnte nicht gestartet werden.");
      setIsStartingCheckout(false);
    }
  };

  const runAnalysis = async () => {
    if (!authUser) {
      setAnalysisError("Bitte zuerst einloggen, damit Checks Ihrem Konto und der History zugeordnet werden koennen.");
      return;
    }
    setIsAnalyzing(true);
    setAnalysisError(null);
    setPaywallBilling(null);
    try {
      const combinedInput = buildCombinedInput();
      const r = await analyzeGridcheck(combinedInput, {
        requestedOfferId: selectedOfferId === "free" ? "free" : selectedOfferId,
      });
      setResult(r);
      setFeedbackType("bestaetigt");
      setFeedbackDecision(decisionFromResult(r));
      setFeedbackComment("");
      setFeedbackMessage(null);
      window.localStorage.removeItem(DRAFT_STORAGE_KEY);
      setStep(2);
      await refreshBillingStatus();
    } catch (err) {
      if (err instanceof AnalyzeApiError) {
        setAnalysisError(err.message);
        if (err.status === 401) {
          setAuthUser(null);
          setBillingStatus(null);
          setPaywallBilling(null);
        }
        if (err.status === 402) {
          setPaywallBilling(err.detail?.billing ?? null);
          await refreshBillingStatus();
        }
      } else {
        setAnalysisError("Analyse konnte nicht gestartet werden.");
      }
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handlePdfExport = async () => {
    if (!authUser) {
      setAnalysisError("Bitte zuerst einloggen, um den PDF-Report herunterzuladen.");
      return;
    }
    if (!result) {
      setAnalysisError("Bitte zuerst eine Analyse durchfuehren, bevor der PDF-Report exportiert wird.");
      return;
    }
    setIsExporting(true);
    setAnalysisError(null);
    setPaywallBilling(null);
    try {
      const stakeholder = stakeholderPath;
      const exportScope = selectedAnalysisOption?.report_scope ?? selectedPackageScope ?? "report";
      const { blob, filename } = await exportStakeholderPdf(buildCombinedInput(), stakeholder, {
        requestedOfferId: selectedOfferId === "free" ? "free" : selectedOfferId,
        analysisRunId: result.history?.analysis_run_id,
      });
      downloadBlobFile(blob, filename || `gridcheck-${stakeholder}-${exportScope}.pdf`);
    } catch (err) {
      if (err instanceof AnalyzeApiError) {
        setAnalysisError(err.message);
        if (err.status === 401) {
          setAuthUser(null);
          setBillingStatus(null);
        }
        if (err.status === 402) {
          setPaywallBilling(err.detail?.billing ?? null);
          await refreshBillingStatus();
        }
      } else {
        setAnalysisError("PDF-Export konnte nicht gestartet werden. Bitte erneut versuchen.");
      }
    } finally {
      setIsExporting(false);
    }
  };

  const handleKiFeedbackSubmit = async () => {
    if (!result?.revision?.hash) {
      setFeedbackMessage("Kein revisionssicherer Analyse-Hash vorhanden.");
      return;
    }
    const kiEntscheidung = decisionFromResult(result);
    setIsSubmittingFeedback(true);
    setFeedbackMessage(null);
    try {
      const response = await submitKiFeedback({
        feedback_typ: feedbackType,
        ki_entscheidung: kiEntscheidung,
        nb_entscheidung: feedbackType === "korrigiert" ? feedbackDecision : undefined,
        kommentar: feedbackComment || undefined,
        revision_hash: result.revision.hash,
        score_gesamt: result.score,
        confidence_snapshot: result.ki.konfidenz_prozent,
        anomaly_flags: result.ki.anomalie_check.flags,
        quelle: "netzbetreiber",
      });
      setFeedbackMessage(
        `Feedback gespeichert. Lernstatus: ${response.lernstatus.status}, Samples ${response.lernstatus.samples_total}.`
      );
    } catch (err) {
      if (err instanceof AnalyzeApiError) {
        setFeedbackMessage(err.message);
      } else {
        setFeedbackMessage("KI-Feedback konnte nicht gespeichert werden.");
      }
    } finally {
      setIsSubmittingFeedback(false);
    }
  };

  const sectionClass = "rounded-2xl border border-gray-700 bg-gray-800/60 p-4 md:p-5";
  const sectionTitle = "mb-3 text-lg font-semibold text-white";
  const labelClass = "mb-1 block text-sm text-gray-300";
  const inputClass = "w-full rounded-xl border border-gray-600 bg-gray-900 px-3 py-2.5 text-sm text-white focus:border-blue-500 focus:outline-none";
  const selectClass = inputClass;
  const fmt = (n: number, d = 1) => Number(n).toFixed(d);
  const decisionFromResult = (value: GridCheckResult): "A" | "B" | "C" => {
    if (value.machbarkeit_stufe === "gruen") return "A";
    if (value.machbarkeit_stufe === "gelb" || value.machbarkeit_stufe === "orange") return "B";
    return "C";
  };
  const stepLabels = ["Anwendungsfall", "Eingaben", "Ergebnis"];
  const canStartAnalysis =
    Boolean(authUser) &&
    !isBillingLoading &&
    (billingStatus ? billingStatus.can_run_analysis : true);
  const effectiveBillingStatus = paywallBilling ?? billingStatus;

  function billingStatusTitle(status: BillingStatus) {
    if (status.subscription_state === "past_due") return "Pro Zahlung offen";
    if (status.subscription_state === "checkout_pending") return "Pro Freischaltung in Pruefung";
    if (status.subscription_state === "canceled") return "Pro Lizenz beendet";
    if (status.has_active_subscription) return "Pro Lizenz aktiv";
    if (status.has_prepaid_credits) return "Bezahlte Credits aktiv";
    return "Free Tier aktiv";
  }

  function billingStatusText(status: BillingStatus) {
    if (status.billing_attention?.message) return status.billing_attention.message;
    if (status.has_active_subscription) return "Laufende Projektpipeline mit aktiver SaaS-Lizenz.";
    if (status.has_prepaid_credits) {
      return `${status.active_paid_entitlements_count} aktives Paket mit sofort nutzbaren Credits vorhanden.`;
    }
    return `${status.free_checks_remaining} von ${status.free_checks_limit} kostenlosen Checks verfuegbar.`;
  }
  const visibleOffers: BillingOffer[] = billingStatus?.catalog?.offers ?? [];
  const addOns: BillingOffer[] = billingStatus?.catalog?.addons ?? [];
  const analysisOptions: BillingAnalysisOption[] = billingStatus?.analysis_options ?? [];
  const selectedAnalysisOption =
    analysisOptions.find((option) => option.offer_id === selectedOfferId) ?? analysisOptions[0] ?? null;
  const selectedPackageScope = selectedAnalysisOption?.package_scope ?? (selectedOfferId === "free" ? "basic" : undefined);
  const selectedPackageProfile = getOfferProfile(selectedAnalysisOption?.offer_id ?? selectedOfferId, selectedPackageScope);
  const selectedPackageWarnings = getPackageBoundaryWarnings(buildCombinedInput(), selectedPackageScope);

  const analysisOptionLabel = (option: BillingAnalysisOption) => {
    if (option.offer_id === "free") {
      return `Free Check (${option.remaining_credits ?? 0} frei)`;
    }
    const creditText =
      option.remaining_credits === null || option.remaining_credits === undefined
        ? "laufend"
        : `${option.remaining_credits} Credit${option.remaining_credits === 1 ? "" : "s"}`;
    return `${option.label} (${creditText})`;
  };

  const resetWorkflow = () => {
    const preferences = readUserPreferences();

    setStep(forcedCustomerType ? 1 : 0);
    setInput({ ...INITIAL_INPUT });
    setMeta({
      ...INITIAL_META,
      kundentyp: forcedCustomerType ?? preferences.defaultCustomerType ?? "",
    });
    setResult(null);
    setAnalysisError(null);
    setFeedbackType("bestaetigt");
    setFeedbackDecision("B");
    setFeedbackComment("");
    setFeedbackMessage(null);
    setAnalysisRunId(createAnalysisRunId());
    setSelectedOfferId("free");
    setPackageSelectionTouched(false);
    setActiveDemoId(null);
    window.localStorage.removeItem(DRAFT_STORAGE_KEY);
  };

  // ==================== STEP 0: Kundentyp ====================
  if (step === 0 && !forcedCustomerType) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="rounded-[28px] border border-gray-700 bg-gray-900/60 p-5 text-center md:p-8">
          <div className="mx-auto inline-flex rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-brand-cyan">
            {stepLabels[0]}
          </div>
          <h2 className="mt-4 text-2xl font-bold text-white md:text-3xl">Waehlen Sie Ihren Anwendungsfall</h2>
          <p className="mx-auto mt-3 max-w-2xl text-sm leading-6 text-gray-400">
            Der Einstieg steuert die Form-Voreinstellung, Ergebnisdarstellung und den spaeteren PDF-Export.
          </p>
          {meta.kundentyp ? (
            <p className="mt-4 text-sm text-brand-cyan">
              Vorauswahl aktiv: {CUSTOMER_LABELS[meta.kundentyp as CustomerType]}
            </p>
          ) : null}
        </div>

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          {(Object.keys(CUSTOMER_LABELS) as CustomerType[]).map((key) => (
            <button
              key={key}
              onClick={() => {
                updateMeta({ kundentyp: key });
                setStep(1);
              }}
              className={`rounded-2xl border p-5 text-left transition group md:p-6 ${
                meta.kundentyp === key
                  ? "border-blue-400 bg-blue-500/10 shadow-[0_0_0_1px_rgba(96,165,250,0.15)]"
                  : "border-gray-700 bg-gray-800/60 hover:border-blue-500"
              }`}
            >
              <div className="mb-2 text-lg font-semibold text-white group-hover:text-blue-400">{CUSTOMER_LABELS[key]}</div>
              <div className="text-sm text-gray-400">{CUSTOMER_DESC[key]}</div>
            </button>
          ))}
        </div>
      </div>
    );
  }

  // ==================== STEP 1: Eingaben ====================
  if (step === 1) {
    return (
      <div className="mx-auto max-w-4xl space-y-6">
        <div className="rounded-[28px] border border-gray-700 bg-gray-900/60 p-5 md:p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div>
              <div className="inline-flex rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-brand-cyan">
                {stepLabels[1]}
              </div>
              <h2 className="mt-4 text-2xl font-bold text-white md:text-3xl">{stakeholderCopy.heroTitle}</h2>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-gray-400">
                {stakeholderCopy.heroDescription}
              </p>
            </div>
            <span className="inline-flex w-fit rounded-full bg-gray-800 px-3 py-1 text-sm text-gray-300">
              {CUSTOMER_LABELS[ct]}
            </span>
          </div>

          <div className="mt-5 grid gap-2 sm:grid-cols-3">
            {stepLabels.map((label, index) => (
              <div
                key={label}
                className={`rounded-2xl border px-3 py-3 text-sm ${
                  index === step
                    ? "border-blue-400/40 bg-blue-500/10 text-white"
                    : index < step
                      ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
                      : "border-white/10 bg-white/5 text-gray-400"
                }`}
              >
                <div className="text-xs uppercase tracking-[0.18em]">{`Schritt ${index + 1}`}</div>
                <div className="mt-1 font-medium">{label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-amber-400/20 bg-amber-500/10 p-4 text-sm leading-6 text-amber-100">
          {stakeholderCopy.visibilityNote}
        </div>

        <DemoCaseLoader onSelect={applyDemoCase} />
        {activeDemoId ? (
          <DemoModeBanner
            title="Beispieldaten aktiv"
            description="Die Eingaben stammen aus einem Demo-Fall ohne echte Netzbetreiberdaten. Ergebnisse dienen der Produktdemonstration."
          />
        ) : null}

        <div className={sectionClass}>
          <h3 className={sectionTitle}>Zugang & Tarif</h3>
          {!authUser ? (
            <div className="space-y-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4">
              <p className="text-sm text-amber-100">
                Checks werden jetzt Ihrem Konto und der Analyse-History zugeordnet. Bitte melden Sie sich an, bevor Sie
                eine Analyse starten.
              </p>
              <div className="flex flex-col gap-3 sm:flex-row">
                <Link
                  href="/login"
                  className="inline-flex items-center justify-center rounded-xl bg-brand-orange px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-orangeHover"
                >
                  Login
                </Link>
                <Link
                  href="/register"
                  className="inline-flex items-center justify-center rounded-xl border border-white/15 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
                >
                  Konto anlegen
                </Link>
              </div>
            </div>
          ) : isBillingLoading ? (
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4 text-sm text-gray-300">
              Tarifstatus wird geladen...
            </div>
          ) : billingStatus ? (
            <div className="space-y-4 rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="flex flex-col gap-3 md:flex-row md:items-start md:justify-between">
                <div>
                  <p className="text-sm font-semibold text-white">
                    {billingStatusTitle(billingStatus)}
                  </p>
                  <p className="mt-1 text-sm text-gray-300">
                    {billingStatusText(billingStatus)}
                  </p>
                  <p className="mt-2 text-sm text-gray-400">{billingStatus.catalog.headline}</p>
                  {billingStatus.current_period_end ? (
                    <p className="mt-1 text-xs text-gray-400">
                      Aktuelle Periode bis {new Date(billingStatus.current_period_end).toLocaleDateString("de-DE")}
                    </p>
                  ) : null}
                </div>
                <div className="flex flex-wrap gap-2">
                  <span className="rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-medium text-brand-cyan">
                    {billingStatus.plan_tier.toUpperCase()}
                  </span>
                  <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-gray-300">
                    {billingStatus.billing_state_label}
                  </span>
                </div>
              </div>
              <div className="grid gap-3 xl:grid-cols-2">
                {analysisOptions.length > 0 ? (
                  <div className="xl:col-span-2 rounded-2xl border border-brand-cyan/20 bg-brand-cyan/10 p-4">
                    <p className="text-sm font-semibold text-white">Analysepaket fuer diesen Run</p>
                    <p className="mt-1 text-sm text-gray-300">
                      Credits werden erst bei erfolgreichem Abschluss verbucht. Professional markiert den Run fuer
                      einen sichtbaren Service-Nachlauf, Express bleibt ein separater Zeit-Zusatz.
                    </p>
                    <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
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
                                ? "border-brand-cyan bg-brand-cyan/15 shadow-[0_0_0_1px_rgba(34,211,238,0.15)]"
                                : "border-white/10 bg-black/10 hover:border-brand-cyan/40"
                            }`}
                          >
                            <p className="text-sm font-semibold text-white">{analysisOptionLabel(option)}</p>
                            <p className="mt-1 text-xs uppercase tracking-[0.14em] text-gray-400">
                              Scope {option.package_scope}
                            </p>
                            <p className="mt-3 text-xs text-gray-400">
                              {option.feature_flags?.visualization
                                ? "Visualisierung / vertiefte Reporttiefe verfuegbar."
                                : option.package_scope === "basic"
                                  ? "Kompakter Kernreport ohne Premium-Vertiefung."
                                  : "Vertiefte Paketlogik fuer Hybrid, Speicher und Trasse."}
                            </p>
                            {option.ops_followup_required ? (
                              <p className="mt-2 text-xs text-amber-200">Betreuter Service-Nachlauf erforderlich.</p>
                            ) : null}
                          </button>
                        );
                      })}
                    </div>
                    {selectedAnalysisOption ? (
                      <p className="mt-3 text-xs text-gray-300">
                        Aktive Auswahl: {analysisOptionLabel(selectedAnalysisOption)}.
                      </p>
                    ) : null}
                    <div className="mt-4 grid gap-3 md:grid-cols-3">
                      <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-500">Produktpfad</div>
                        <p className="mt-2 text-sm font-semibold text-white">{selectedPackageProfile.title}</p>
                        <p className="mt-2 text-xs leading-5 text-gray-400">{selectedPackageProfile.audience}</p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-500">Lieferumfang</div>
                        <p className="mt-2 text-sm font-semibold text-white">
                          {getPackageScopeLabel(selectedPackageScope)} ·{" "}
                          {getReportScopeLabel(selectedAnalysisOption?.report_scope)}
                        </p>
                        <p className="mt-2 text-xs leading-5 text-gray-400">{selectedPackageProfile.deliverable}</p>
                      </div>
                      <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
                        <div className="text-xs uppercase tracking-[0.18em] text-gray-500">Abgrenzung</div>
                        <p className="mt-2 text-sm font-semibold text-white">{selectedPackageProfile.badge}</p>
                        <p className="mt-2 text-xs leading-5 text-gray-400">{selectedPackageProfile.boundary}</p>
                      </div>
                    </div>
                    <p className="mt-3 text-xs text-gray-300">Naechster Schritt: {selectedPackageProfile.nextStep}</p>
                    {selectedPackageWarnings.length > 0 ? (
                      <div className="mt-4 rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4">
                        <p className="text-sm font-semibold text-amber-100">Hinweis zur Paketgrenze</p>
                        <ul className="mt-2 space-y-1 text-xs leading-5 text-amber-100/90">
                          {selectedPackageWarnings.map((warning) => (
                            <li key={warning}>{warning}</li>
                          ))}
                        </ul>
                      </div>
                    ) : null}
                    <div className="mt-4 rounded-2xl border border-white/10 bg-black/10 p-4 text-xs leading-5 text-gray-400">
                      <p className="font-semibold text-white">Professional, Express und VNB Pilot werden getrennt gefuehrt.</p>
                      <p className="mt-2">
                        Professional erweitert den Reportscope und erzeugt sichtbaren Service-Nachlauf. Express ist nur
                        ein Zeit-Zusatz. VNB Pilot bleibt ein eigener Kontakt- und Pilotpfad ausserhalb des
                        Self-Serve-Upgrades.
                      </p>
                    </div>
                  </div>
                ) : null}
                {visibleOffers.map((offer) => {
                  const isSubscription = offer.offer_id === "pro_lizenz";
                  const isContactOnly = offer.billing_mode === "contact";
                  const subscriptionBlockedByPastDue = isSubscription && billingStatus.subscription_state === "past_due";
                  return (
                    <div
                      key={offer.offer_id}
                      className={`rounded-2xl border p-4 ${
                        offer.featured
                          ? "border-brand-cyan/35 bg-brand-cyan/10"
                          : "border-white/10 bg-black/10"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-white">{offer.name}</p>
                          <p className="mt-1 text-lg font-semibold text-white">{offer.price_label}</p>
                        </div>
                        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-gray-300">
                          {offer.category === "saas" ? "SaaS" : offer.category === "pilot" ? "Pilot" : "Pay-per-Use"}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-gray-200">{offer.tagline}</p>
                      <p className="mt-2 text-sm text-gray-400">{offer.summary}</p>
                      <p className="mt-3 text-xs text-gray-400">Ideal fuer: {offer.recommended_for}</p>
                      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        {isContactOnly ? (
                          <Link
                            href="/contact"
                            className="inline-flex items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
                          >
                            {offer.cta_label}
                          </Link>
                        ) : subscriptionBlockedByPastDue ? (
                          <Link
                            href="/settings"
                            className="inline-flex items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
                          >
                            Billing Portal oeffnen
                          </Link>
                        ) : (
                          <button
                            type="button"
                            onClick={() => handleUpgradeCheckout(offer.offer_id)}
                            disabled={!offer.checkout_enabled || isStartingCheckout}
                            className={`rounded-xl px-4 py-2.5 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-60 ${
                              isSubscription
                                ? "bg-brand-cyan text-black hover:bg-brand-cyan/90"
                                : "bg-brand-orange text-white hover:bg-brand-orangeHover"
                            }`}
                          >
                            {isStartingCheckout ? "Checkout startet..." : offer.cta_label}
                          </button>
                        )}
                        {offer.self_serve_unlock ? (
                          <span className="text-xs text-brand-cyan">Self-Serve Unlock</span>
                        ) : (
                          <span className="text-xs text-gray-500">Service-/Projektpfad</span>
                        )}
                      </div>
                      {subscriptionBlockedByPastDue ? (
                        <p className="mt-3 text-xs text-amber-200">
                          Pro ist wegen offener Zahlung aktuell fuer neue Analysen gesperrt. One-off-Pakete bleiben nutzbar.
                        </p>
                      ) : null}
                    </div>
                  );
                })}
              </div>
              {addOns.length > 0 ? (
                <div className="rounded-2xl border border-dashed border-white/15 bg-black/10 p-4">
                  <p className="text-sm font-semibold text-white">Optionale Add-ons</p>
                  <div className="mt-3 flex flex-wrap gap-3">
                    {addOns.map((offer) => (
                      <div key={offer.offer_id} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                        <p className="text-sm font-medium text-white">{offer.name}</p>
                        <p className="mt-1 text-xs text-gray-400">{offer.tagline}</p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}
              {!billingStatus.has_active_subscription ? (
                <div className="rounded-2xl border border-white/10 bg-black/10 p-4 text-sm text-gray-400">
                  {billingStatus.has_prepaid_credits
                    ? "Bezahlte Credits sind aktiv. Die serverseitige Paketlogik entscheidet pro Run ueber Scope und Verbrauch."
                    : "Nach 3 Checks sperrt die Paywall serverseitig. Fuer laufende Self-Serve-Nutzung ist die Pro Lizenz der direkte Unlock-Pfad; die Pay-per-Use-Angebote sind bereits sichtbar und buchbar vorbereitet."}
                </div>
              ) : null}
            </div>
          ) : (
            <div className="rounded-2xl border border-red-700 bg-red-900/30 p-4 text-sm text-red-200">
              Tarifstatus konnte nicht geladen werden.
            </div>
          )}
        </div>

        {/* Projektdaten */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Projektdaten</h3>
          <p className="mb-4 text-sm leading-6 text-gray-400">{stakeholderCopy.formIntro}</p>
          <div className="grid gap-4 md:grid-cols-2">
            <div>
              <label className={labelClass}>Projektname</label>
              <input className={inputClass} value={meta.projektname} onChange={e => updateMeta({ projektname: e.target.value })} placeholder="z.B. Solarpark Musterstadt" />
            </div>
            <div>
              <label className={labelClass}>PLZ</label>
              <input className={inputClass} value={input.plz} onChange={e => updateInput({ plz: e.target.value })} placeholder="z.B. 30159" maxLength={5} inputMode="numeric" />
            </div>
            <div>
              <label className={labelClass}>Ort</label>
              <input className={inputClass} value={meta.ort} onChange={e => updateMeta({ ort: e.target.value })} placeholder="z.B. Hannover" />
            </div>
            <div>
              <label className={labelClass}>Erzeugungstyp</label>
              <select className={selectClass} value={meta.erzeugungstyp} onChange={e => updateMeta({ erzeugungstyp: e.target.value })}>
                <option value="">-- Wählen --</option>
                {ERZEUGUNGS_OPTIONEN[ct]?.map(o => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          </div>
          <VnbBanner plz={input.plz} />
        </div>

        {/* Technische Daten */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Technische Parameter</h3>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className={labelClass}>Anschlussleistung (kW)</label>
              <input type="number" className={inputClass} value={input.anschlussleistung_kw} onChange={e => updateInput({ anschlussleistung_kw: Number(e.target.value) })} />
            </div>
            <div>
              <label className={labelClass}>Spannungsebene</label>
              <select className={selectClass} value={input.spannungsebene} onChange={e => updateInput({ spannungsebene: e.target.value as Spannungsebene })}>
                <option value="NS">NS (0,4 kV)</option>
                <option value="MS">MS (20 kV)</option>
                <option value="HS">HS (110 kV)</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>cos phi</label>
              <input type="number" step="0.01" min="0.8" max="1" className={inputClass} value={input.cos_phi} onChange={e => updateInput({ cos_phi: Number(e.target.value) })} />
            </div>
            <div>
              <label className={labelClass}>Richtung</label>
              <select className={selectClass} value={input.richtung} onChange={e => updateInput({ richtung: e.target.value as GridCheckInput["richtung"] })}>
                <option value="einspeisung">Einspeisung</option>
                <option value="bezug">Bezug</option>
                <option value="bidirektional">Bidirektional</option>
              </select>
            </div>
            <div>
              <label className={labelClass}>Entfernung NVP (km)</label>
              <input type="number" step="0.1" className={inputClass} value={input.entfernung_km ?? ""} onChange={e => updateInput({ entfernung_km: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
              <p className="mt-1 text-xs text-gray-500">{cableLengthHint.annahme}</p>
            </div>
          </div>
          <p className="mt-3 rounded-xl border border-blue-500/20 bg-blue-500/10 px-3 py-2 text-xs leading-5 text-blue-100">
            <span className="font-semibold">Leistungsrichtwert {powerLimitHints.label}:</span> typisch bis ca.{" "}
            {powerLimitHints.typicalMaxKw.toLocaleString("de-DE")} kW (Screening bis ca.{" "}
            {powerLimitHints.screeningUpperKw.toLocaleString("de-DE")} kW). {powerLimitHints.hinweis}
            {powerLimitHints.ueberTypischemRichtwert ? " Ihre Eingabe liegt über dem typischen Richtwert." : ""}
          </p>
          {cosPhiHint.quelle === "rolle_default" ? (
            <p className="mt-2 text-xs text-gray-500">
              cos φ Standard für diese Anlagenrolle: {cosPhiHint.cosPhi} (kann im Feld überschrieben werden).
            </p>
          ) : null}
        </div>

        <ProjectProfileFields value={input} onChange={(next) => setInput((prev) => ({ ...prev, ...next }))} />

        {/* Optionale Netzdaten */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Netzdaten (optional - erhoehen Genauigkeit)</h3>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className={labelClass}>Sk min (MVA)</label>
              <input type="number" step="1" className={inputClass} value={input.sk_min_mva ?? ""} onChange={e => updateInput({ sk_min_mva: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
            <div>
              <label className={labelClass}>Sk max (MVA)</label>
              <input type="number" step="1" className={inputClass} value={input.sk_max_mva ?? ""} onChange={e => updateInput({ sk_max_mva: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
            <div>
              <label className={labelClass}>R/X Verhaeltnis</label>
              <input type="number" step="0.1" className={inputClass} value={input.rx_verhaeltnis ?? ""} onChange={e => updateInput({ rx_verhaeltnis: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
            <div>
              <label className={labelClass}>Trafo Sr (kVA)</label>
              <input type="number" className={inputClass} value={input.trafo_sr_kva ?? ""} onChange={e => updateInput({ trafo_sr_kva: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
            <div>
              <label className={labelClass}>Trafo uk (%)</label>
              <input type="number" step="0.1" className={inputClass} value={input.trafo_uk_pct ?? ""} onChange={e => updateInput({ trafo_uk_pct: e.target.value ? Number(e.target.value) : undefined })} placeholder="auto" />
            </div>
            <div>
              <label className={labelClass}>VNB-Kapazitätsangabe (kW)</label>
              <input
                type="number"
                className={inputClass}
                value={input.netzkapazitaet_kw ?? ""}
                onChange={(e) =>
                  updateInput({ netzkapazitaet_kw: e.target.value ? Number(e.target.value) : undefined })
                }
                placeholder="optional"
              />
              <p className="mt-1 text-xs text-gray-500">
                Nur als Nutzer- oder VNB-Hinweis – keine verifizierte freie Netzkapazität ohne belastbare VNB-Daten.
              </p>
            </div>
          </div>
        </div>

        {isAnalyzing ? <AnalysisProgressPanel active className="mb-4" /> : null}

        {analysisError && (
          <div className="rounded-2xl border border-red-700 bg-red-900/30 p-3 text-sm text-red-200">
            {analysisError}
          </div>
        )}

        {effectiveBillingStatus?.upgrade_required && effectiveBillingStatus.subscription_state !== "checkout_pending" ? (
          <BillingUpgradePrompt
            billing={effectiveBillingStatus}
            onCheckout={handleUpgradeCheckout}
            isStartingCheckout={isStartingCheckout}
          />
        ) : null}

        {/* Buttons */}
        <div className="sticky bottom-3 z-20 pt-2">
          <div className="flex flex-col gap-3 rounded-[24px] border border-gray-700 bg-gray-900/95 p-3 shadow-2xl backdrop-blur sm:flex-row sm:items-center sm:justify-between">
            <div className="text-sm text-gray-400">
              {!authUser
                ? "Bitte erst einloggen, damit Checks gespeichert und der History zugeordnet werden."
                : billingStatus?.subscription_state === "past_due"
                  ? "Pro Zahlung offen: Bitte Billing-Portal pruefen oder ein separates One-off-Paket fuer neue Analysen nutzen."
                  : billingStatus?.subscription_state === "checkout_pending"
                    ? "Checkout erkannt: Freischaltung wird noch von Stripe bestaetigt."
                    : billingStatus?.subscription_state === "canceled"
                      ? "Pro beendet: Fuer Reaktivierung bitte Billing-Portal oder neuen Checkout nutzen."
                    : billingStatus?.has_active_subscription
                      ? "Pro aktiv: Analysen werden Ihrem Konto und der History revisionssicher zugeordnet."
                  : billingStatus?.has_prepaid_credits
                    ? `Credits aktiv: ${billingStatus?.active_paid_entitlements_count ?? 0} Paket(e) mit nutzbaren Credits verfuegbar.`
                    : `Free Tier: ${billingStatus?.free_checks_remaining ?? "?"} kostenlose Checks verbleiben.`}
            </div>
            <div className="flex flex-col-reverse gap-3 sm:flex-row">
              <button
                onClick={() => setStep(0)}
                className="rounded-xl border border-gray-600 px-5 py-2.5 text-sm text-gray-300 transition hover:text-white"
              >
                Zurueck
              </button>
              <button
                onClick={runAnalysis}
                disabled={isAnalyzing || !canStartAnalysis}
                className="rounded-xl bg-gradient-to-r from-blue-600 to-purple-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:from-blue-500 hover:to-purple-500 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isAnalyzing
                  ? "Analyse laeuft..."
                  : !authUser
                    ? "Login erforderlich"
                    : billingStatus?.subscription_state === "past_due" && !billingStatus.can_run_analysis
                      ? "Zahlung pruefen oder Paket waehlen"
                    : billingStatus && !billingStatus.can_run_analysis
                      ? "Upgrade erforderlich"
                      : "Analyse starten"}
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // ==================== STEP 2: Ergebnis ====================
  if (step === 2 && result) {
    const scoreColor = result.score >= 70 ? "text-green-400" : result.score >= 50 ? "text-yellow-400" : result.score >= 30 ? "text-orange-400" : "text-red-400";
    const stufeLabels: Record<string, string> = { gruen: "Machbar", gelb: "Bedingt machbar", orange: "Eingeschraenkt", rot: "Kritisch" };
    const stufeColors: Record<string, string> = { gruen: "bg-green-600", gelb: "bg-yellow-600", orange: "bg-orange-600", rot: "bg-red-600" };
    const n1Headline =
      result.n1.n1_sicher === true
        ? "screeningseitig plausibel"
        : result.n1.n1_sicher === false
          ? "kritischer N-1-Hinweis"
          : "vorlaeufig / offen";
    const scoreRows = [
      { label: "Kapazität", val: result.teil_scores.kapazitaet, max: 25 },
      { label: "Spannung", val: result.teil_scores.spannung, max: 25 },
      { label: "Kurzschluss", val: result.teil_scores.kurzschluss, max: 20 },
      { label: "N-1 Sicherheit", val: result.teil_scores.n1, max: 15 },
      { label: "Datenqualitaet", val: result.teil_scores.datenqualitaet, max: 15 },
    ];
    const gewichteteSumme = scoreRows.reduce((acc, s) => acc + (s.val * s.max) / 100, 0);
    const combinedInput = buildCombinedInput();
    const resultPackageProfile = getOfferProfile(result.billing_access?.offer_id, result.billing_access?.package_scope);
    const resultPackageWarnings = getPackageBoundaryWarnings(combinedInput, result.billing_access?.package_scope);
    const costBand = buildIndicativeCostBand(result);
    const projektiererGuidance = buildProjektiererGuidance(result);
    const fieldCaptureHref = buildSiteMarkerHref({
      source: "check",
      projectName: meta.projektname,
      plz: combinedInput.plz,
      ort: combinedInput.ort,
      latitude: combinedInput.project_location?.latitude,
      longitude: combinedInput.project_location?.longitude,
      returnTo: "/",
    });
    const followupHref = result.billing_access?.ops_followup_required ? "/settings" : "/projects";
    const followupLabel = result.billing_access?.ops_followup_required
      ? "Service- und Tarifstatus oeffnen"
      : "Im Projekt-Workspace weiterarbeiten";

    return (
      <div className="mx-auto max-w-5xl space-y-6">
        <AnalysisDisclaimer />
        {/* Header */}
        <div className="rounded-[28px] border border-gray-700 bg-gray-900/60 p-5 md:p-6">
          <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div>
              <div className="inline-flex rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.22em] text-brand-cyan">
                {stepLabels[2]}
              </div>
              <h2 className="mt-4 text-2xl font-bold text-white md:text-3xl">
                {stakeholderCopy.resultTitle}: {meta.projektname || "Netzanschluss-Analyse"}
              </h2>
              <p className="mt-2 text-sm text-gray-400">
                {stakeholderCopy.summaryLead}
              </p>
            </div>
            <div className="flex flex-wrap items-center gap-3">
              <span className={`${stufeColors[result.machbarkeit_stufe]} rounded-full px-4 py-1 text-sm font-semibold text-white`}>
                {stufeLabels[result.machbarkeit_stufe]}
              </span>
              <span className={`text-3xl font-bold ${scoreColor}`}>{result.score}/100</span>
              <span className="text-sm text-gray-400">
                Confidence: {result.daten_confidence} / KI {fmt(result.ki.konfidenz_prozent, 0)}%
              </span>
            </div>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-3">
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-gray-400">Kapazitaet</div>
              <div className="mt-1 text-xl font-semibold text-white">{fmt(result.teil_scores.kapazitaet, 0)}%</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-gray-400">N-1 Nachweistiefe</div>
              <div className="mt-1 text-xl font-semibold text-white">{result.n1.n1_klasse ?? "N1-0"}</div>
              <div className="mt-1 text-xs text-gray-400">{n1Headline}</div>
            </div>
            <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
              <div className="text-xs uppercase tracking-[0.18em] text-gray-400">Netzausbau</div>
              <div className="mt-1 text-xl font-semibold text-white">{result.netzausbau_erforderlich ? "Voraussichtlich ja" : "Derzeit kein Hinweis"}</div>
            </div>
          </div>
        </div>

        {(result.connection_type_label || result.power_limit_hints) ? (
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Anschluss & Leistungsrahmen</h3>
            <div className="grid gap-3 text-sm text-gray-300 md:grid-cols-2">
              {result.connection_type_label ? (
                <p>
                  <span className="text-gray-400">Anschlussart:</span>{" "}
                  <span className="text-white font-medium">{result.connection_type_label}</span>
                </p>
              ) : null}
              {result.power_limit_hints ? (
                <p>
                  <span className="text-gray-400">Leistungsrichtwert {result.power_limit_hints.label}:</span>{" "}
                  typisch bis ca. {result.power_limit_hints.typical_max_kw.toLocaleString("de-DE")} kW
                  {result.power_limit_hints.ueber_typischem_richtwert ? " — Eingabe über typischem Richtwert." : ""}
                </p>
              ) : null}
            </div>
            {result.power_limit_hints?.hinweis ? (
              <p className="mt-2 text-xs leading-5 text-gray-500">{result.power_limit_hints.hinweis}</p>
            ) : null}
          </div>
        ) : null}

        {result.warnings.length > 0 ? (
          <div className="rounded-xl border border-amber-500/30 bg-amber-500/10 p-4">
            <h4 className="text-sm font-semibold text-amber-200">Hinweise & Warnungen</h4>
            <ul className="mt-2 space-y-1 text-sm text-amber-100">
              {result.warnings.map((w, i) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          </div>
        ) : null}

        {result.technical_details ? (
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Technische Details (vorläufig)</h3>
            <div className="grid gap-3 text-sm md:grid-cols-2 lg:grid-cols-4">
              <div className="rounded-lg bg-gray-900 p-3">
                <div className="text-xs text-gray-400">Spannungsfall</div>
                <div className="mt-1 font-mono text-white">
                  {fmt(result.technical_details.spannungsfall?.delta_u_prozent ?? result.delta_u_pct, 2)} %
                </div>
                <div className="mt-1 text-xs text-gray-500">
                  {result.technical_details.spannungsfall?.bewertung ?? result.spannungsbewertung}
                  {result.technical_details.spannungsfall?.cos_phi_annahme
                    ? ` · ${result.technical_details.spannungsfall.cos_phi_annahme}`
                    : ""}
                </div>
              </div>
              <div className="rounded-lg bg-gray-900 p-3">
                <div className="text-xs text-gray-400">Kurzschluss Ik</div>
                <div className="mt-1 font-mono text-white">
                  {fmt(
                    result.technical_details.kurzschluss?.ik_referenz_ka ??
                      result.technical_details.kurzschluss?.ik_max_ka ??
                      result.kurzschluss.ik_max_ka,
                    1,
                  )}{" "}
                  kA
                </div>
                <div className="mt-1 text-xs text-gray-500">
                  {result.technical_details.kurzschluss?.vorlaeufig
                    ? "Vorläufig (Band nach Spannungsebene)"
                    : "Berechnet"}
                  {result.technical_details.kurzschluss?.hinweis
                    ? ` · ${result.technical_details.kurzschluss.hinweis}`
                    : ""}
                </div>
              </div>
              <div className="rounded-lg bg-gray-900 p-3">
                <div className="text-xs text-gray-400">Leitung / Querschnitt</div>
                <div className="mt-1 font-mono text-white">
                  {result.technical_details.leitung?.querschnitt_mm2
                    ? `${result.technical_details.leitung.querschnitt_mm2} mm²`
                    : "—"}
                </div>
                <div className="mt-1 text-xs text-gray-500">
                  {result.technical_details.leitung?.typ ?? "Typ aus Annahme"}
                  {result.technical_details.leitung?.i_max_a
                    ? ` · Imax ${fmt(result.technical_details.leitung.i_max_a, 0)} A`
                    : ""}
                </div>
              </div>
              <div className="rounded-lg bg-gray-900 p-3">
                <div className="text-xs text-gray-400">Trasse</div>
                <div className="mt-1 font-mono text-white">
                  {fmt(result.technical_details.trasse?.entfernung_km ?? result.nvp_entfernung_km, 2)} km
                </div>
                <div className="mt-1 text-xs text-gray-500">
                  {result.technical_details.trasse?.heuristisch
                    ? "Heuristische Entfernung (keine GPS-Messung)"
                    : "Nutzereingabe"}
                  {result.technical_details.trasse?.annahme
                    ? ` · ${result.technical_details.trasse.annahme}`
                    : ""}
                </div>
              </div>
            </div>
          </div>
        ) : null}
        </div>

        <div className="grid gap-4 lg:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-gray-400">Produktpfad dieses Runs</div>
            <p className="mt-2 text-lg font-semibold text-white">{resultPackageProfile.title}</p>
            <p className="mt-2 text-sm leading-6 text-gray-300">{resultPackageProfile.deliverable}</p>
            <div className="mt-3 flex flex-wrap gap-2 text-xs">
              <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-white">
                {getPackageScopeLabel(result.billing_access?.package_scope)}
              </span>
              <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-white">
                {getReportScopeLabel(result.billing_access?.report_scope)}
              </span>
              {result.history?.analysis_run_id ? (
                <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-white">
                  Run #{result.history.analysis_run_id}
                </span>
              ) : null}
            </div>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-gray-400">Naechste Nutzerfuehrung</div>
            <p className="mt-2 text-sm leading-6 text-gray-300">{resultPackageProfile.nextStep}</p>
            <p className="mt-3 text-xs leading-5 text-gray-500">{resultPackageProfile.boundary}</p>
            {result.billing_access?.ops_followup_required ? (
              <p className="mt-3 rounded-xl border border-amber-400/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-100">
                Dieser Run markiert einen sichtbaren Service-Nachlauf statt eines stillen Self-Serve-Abschlusses.
              </p>
            ) : null}
          </div>
        </div>

        {stakeholderPath === "vnb" ? (
          <div className="grid gap-4 md:grid-cols-2">
            <div className={sectionClass}>
              <h3 className={sectionTitle}>VNB-Prozesssicht</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li>Antragskern: {combinedInput.plz && combinedInput.anschlussleistung_kw > 0 ? "plausibel vorbereitet" : "noch unvollstaendig"}</li>
                <li>N-1-Nachweistiefe: {result.n1.n1_klasse ?? "N1-0"}</li>
                <li>Audit-Hash: {result.revision?.hash ?? "noch offen"}</li>
                <li>{stakeholderCopy.visibilityNote}</li>
              </ul>
            </div>
            <div className={sectionClass}>
              <h3 className={sectionTitle}>Technische Auflagen</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                {result.empfehlungen.slice(0, 4).map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="text-blue-400">&#8226;</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : null}

        {stakeholderPath === "invest" ? (
          <div className="grid gap-4 md:grid-cols-2">
            <div className={sectionClass}>
              <h3 className={sectionTitle}>Investsicht: Kostenbandbreite</h3>
              <div className="space-y-2 text-sm text-gray-300">
                <p>Niedrig: <span className="text-white font-semibold">{costBand ? costBand.niedrig.toLocaleString("de-DE") : "offen"} EUR</span></p>
                <p>Basis: <span className="text-white font-semibold">{costBand ? costBand.basis.toLocaleString("de-DE") : "offen"} EUR</span></p>
                <p>Hoch: <span className="text-white font-semibold">{costBand ? costBand.hoch.toLocaleString("de-DE") : "offen"} EUR</span></p>
                {costBand?.confidence ? <p>Confidence: {costBand.confidence}%</p> : null}
                {costBand?.source ? <p>Quelle: {costBand.source}</p> : null}
                {costBand?.drivers?.length ? <p>Risikotreiber: {costBand.drivers.join(" · ")}</p> : null}
              </div>
            </div>
            <div className={sectionClass}>
              <h3 className={sectionTitle}>Due-Diligence-Hinweise</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                <li>Standortbasis: {combinedInput.project_location?.address_hint || combinedInput.ort || combinedInput.plz || "noch grob"}</li>
                <li>Netz-/N-1-Risiko: {result.n1.n1_klasse ?? "N1-0"} · {n1Headline}</li>
                <li>Stakeholder-Fit: {result.erweiterte_scores.stakeholder_fit}/100</li>
                <li>{stakeholderCopy.visibilityNote}</li>
              </ul>
            </div>
          </div>
        ) : null}

        {stakeholderPath === "projektierer" ? (
          <div className="grid gap-4 lg:grid-cols-3">
            <div className={sectionClass}>
              <h3 className={sectionTitle}>Projektierer-Rollenbild im MVP</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                {projektiererGuidance.roles.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="text-blue-400">&#8226;</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className={sectionClass}>
              <h3 className={sectionTitle}>Naechste Vergleichsachsen</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                {projektiererGuidance.compareAxes.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="text-blue-400">&#8226;</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
            <div className={sectionClass}>
              <h3 className={sectionTitle}>VNB- / Invest-Vorbereitung</h3>
              <ul className="space-y-2 text-sm text-gray-300">
                {projektiererGuidance.preparationChecklist.map((item) => (
                  <li key={item} className="flex gap-2">
                    <span className="text-blue-400">&#8226;</span>
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        ) : null}

        {resultPackageWarnings.length > 0 ? (
          <div className="rounded-2xl border border-amber-400/30 bg-amber-500/10 p-4">
            <p className="text-sm font-semibold text-amber-100">Paketgrenze in diesem Ergebnis</p>
            <ul className="mt-2 space-y-1 text-sm leading-6 text-amber-100/90">
              {resultPackageWarnings.map((warning) => (
                <li key={warning}>{warning}</li>
              ))}
            </ul>
          </div>
        ) : null}

        <ProductDecisionGuide
          title="Naechster Produktpfad nach diesem Ergebnis"
          description="Diese Hilfe uebersetzt das aktuelle Ergebnis in einen kaufbaren naechsten Schritt, ohne technische Scope-Grenzen zu verwischen."
          currentOfferId={result.billing_access?.offer_id}
          currentPackageScope={result.billing_access?.package_scope}
          compact
        />

        <div className="grid gap-4 lg:grid-cols-3">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-gray-400">Weiter im MVP</div>
            <p className="mt-2 text-lg font-semibold text-white">Projekt-Workspace statt Sackgasse</p>
            <p className="mt-2 text-sm leading-6 text-gray-300">
              Ueberfuehren Sie den Run in einen dauerhaften Projektkontext, um Analyse, Paketentscheidung und weitere
              Freigaben konsistent weiterzufuehren.
            </p>
            <Link
              href={followupHref}
              className="mt-4 inline-flex h-11 items-center justify-center rounded-xl bg-brand-orange px-4 text-sm font-semibold text-white transition hover:bg-brand-orangeHover"
            >
              {followupLabel}
            </Link>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-gray-400">Vor-Ort-Aufnahme</div>
            <p className="mt-2 text-lg font-semibold text-white">Marker mobil dokumentieren</p>
            <p className="mt-2 text-sm leading-6 text-gray-300">
              Sichtbare Assets, Fotos und Standortindizien lassen sich direkt im Feld erfassen. Der Marker-Flow bleibt
              bewusst dokumentierend und behauptet keine freie Netzkapazitaet.
            </p>
            <Link
              href={fieldCaptureHref}
              className="mt-4 inline-flex h-11 items-center justify-center rounded-xl border border-brand-cyan/20 bg-brand-cyan/10 px-4 text-sm font-semibold text-brand-cyan transition hover:bg-brand-cyan/15"
            >
              Vor-Ort-Marker erfassen
            </Link>
          </div>
          <div className="rounded-2xl border border-white/10 bg-white/5 p-4">
            <div className="text-xs uppercase tracking-[0.18em] text-gray-400">Tarife & Verlauf</div>
            <p className="mt-2 text-lg font-semibold text-white">History und Paketrechte pruefen</p>
            <p className="mt-2 text-sm leading-6 text-gray-300">
              Im Settings-Bereich sehen Sie Run-History, Credits, Pro-Status und den naechsten sinnvollen Upgrade- oder
              Servicepfad.
            </p>
            <Link
              href="/settings"
              className="mt-4 inline-flex h-11 items-center justify-center rounded-xl border border-white/15 bg-white/5 px-4 text-sm font-semibold text-white transition hover:bg-white/10"
            >
              Settings oeffnen
            </Link>
          </div>
        </div>

        {hasNetzplanResult(result) ? (
          <NetzplanVisualization
            input={input}
            result={result}
            meta={{
              kundentyp: meta.kundentyp,
              projektname: meta.projektname,
              ort: meta.ort,
              erzeugungstyp: meta.erzeugungstyp,
            }}
          />
        ) : null}

        {showDeepTechnicalDetails ? (
          <>
            <N1AssessmentPanel result={result} />

            <div className={sectionClass}>
              <h3 className={sectionTitle}>Kerndaten</h3>
              <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
                <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">P</div><div className="text-white font-mono text-lg">{fmt(result.p_max_kW, 1)} kW</div></div>
                <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">S</div><div className="text-white font-mono text-lg">{fmt(result.s_max_kVA, 1)} kVA</div></div>
                <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">I Betrieb</div><div className="text-white font-mono text-lg">{fmt(result.i_betrieb_A, 1)} A</div></div>
                <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Delta u</div><div className="text-white font-mono text-lg">{fmt(result.delta_u_pct, 2)}%</div></div>
              </div>
            </div>
          </>
        ) : (
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Sichtbarkeitsgrenze in der Investsicht</h3>
            <p className="text-sm leading-6 text-gray-300">
              Netzplan, Impedanzmodell und rohe technische Tiefendetails bleiben fuer diesen Produktpfad bewusst
              ausgeblendet. Die Investsicht verdichtet stattdessen Risiko, Kostenbandbreite, Standortqualitaet und
              revisionssichere Einordnung.
            </p>
          </div>
        )}

        {/* Teil-Scores */}
        <div className={sectionClass}>
          <h3 className={sectionTitle}>Bewertung (Teilscores in %, rechts gewichteter Beitrag)</h3>
          <div className="space-y-2">
            {scoreRows.map(s => (
              <div key={s.label} className="grid gap-2 rounded-2xl border border-white/5 bg-black/10 p-3 sm:grid-cols-[128px_minmax(0,1fr)_112px] sm:items-center sm:border-0 sm:bg-transparent sm:p-0">
                <div className="text-sm text-gray-300">{s.label}</div>
                <div className="flex-1 bg-gray-900 rounded-full h-3 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${
                      s.val / 100 > 0.7 ? "bg-green-500" : s.val / 100 > 0.4 ? "bg-yellow-500" : "bg-red-500"
                    }`}
                    style={{ width: `${Math.max(0, Math.min(100, s.val))}%` }}
                  />
                </div>
                <div className="text-sm text-gray-400 sm:text-right">
                  {fmt(s.val, 0)}% ({fmt((s.val * s.max) / 100, 1)}/{s.max})
                </div>
              </div>
            ))}
            <div className="pt-2 text-sm text-gray-300 flex justify-between border-t border-gray-700/70">
              <span>Summe gewichtete Beitraege</span>
              <span className="font-mono">{fmt(gewichteteSumme, 1)}/100</span>
            </div>
            <div className="text-sm text-gray-300 flex justify-between">
              <span>Finaler Score nach Caps</span>
              <span className="font-mono">{fmt(result.score, 1)}/100</span>
            </div>
            {result.score < gewichteteSumme && (
              <div className="text-xs text-yellow-300">
                Hinweis: Score-Caps aus kritischen Kriterien haben den finalen Score reduziert.
              </div>
            )}
          </div>
        </div>

        {showDeepTechnicalDetails ? (
          <>
            <div className={sectionClass}>
              <h3 className={sectionTitle}>Szenarien-Analyse (thermischer Status je Szenario)</h3>
              <div className="space-y-3 md:hidden">
                {result.szenarien.map((s) => (
                  <div key={s.name} className="rounded-2xl border border-gray-700 bg-gray-900 p-4">
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <div className="font-medium text-white">{s.name}</div>
                        <div className="mt-1 text-xs text-gray-400">Delta u {s.delta_u_pct} % | Ik {s.ik_kA} kA</div>
                      </div>
                      <span className={`rounded-full px-2 py-1 text-xs ${s.bewertung === "ok" ? "bg-green-900 text-green-300" : s.bewertung === "grenzwertig" ? "bg-yellow-900 text-yellow-300" : "bg-red-900 text-red-300"}`}>
                        {s.bewertung}
                      </span>
                    </div>
                    <div className="mt-3 grid grid-cols-2 gap-3 text-sm text-gray-300">
                      <div>
                        <div className="text-xs text-gray-500">Trafo</div>
                        <div>{s.trafo_auslastung_pct}%</div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-500">Leitung</div>
                        <div>{s.leitung_auslastung_pct}%</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full text-sm">
                  <thead><tr className="text-gray-400 border-b border-gray-700">
                    <th className="text-left py-2">Szenario</th><th className="text-right">Delta u (%)</th><th className="text-right">Trafo (%)</th><th className="text-right">Leitung (%)</th><th className="text-right">Ik (kA)</th><th className="text-center">Status</th>
                  </tr></thead>
                  <tbody>
                    {result.szenarien.map(s => (
                      <tr key={s.name} className="border-b border-gray-800">
                        <td className="py-2 text-white">{s.name}</td>
                        <td className="text-right text-gray-300">{s.delta_u_pct}</td>
                        <td className="text-right text-gray-300">{s.trafo_auslastung_pct}</td>
                        <td className="text-right text-gray-300">{s.leitung_auslastung_pct}</td>
                        <td className="text-right text-gray-300">{s.ik_kA}</td>
                        <td className="text-center">
                          <span className={`px-2 py-0.5 rounded text-xs ${s.bewertung === "ok" ? "bg-green-900 text-green-300" : s.bewertung === "grenzwertig" ? "bg-yellow-900 text-yellow-300" : "bg-red-900 text-red-300"}`}>{s.bewertung}</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className={sectionClass}>
              <h3 className={sectionTitle}>Kurzschluss</h3>
              <div className="grid gap-3 sm:grid-cols-3">
                <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Ik min</div><div className="text-white font-mono">{result.kurzschluss.ik_min_kA} kA</div></div>
                <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Ik max</div><div className="text-white font-mono">{result.kurzschluss.ik_max_kA} kA</div></div>
                <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Sk am NVP</div><div className="text-white font-mono">{result.kurzschluss.sk_am_nvp_mva} MVA</div></div>
              </div>
              <p className="text-sm text-gray-400 mt-2">{result.kurzschluss.bewertung}</p>
            </div>
          </>
        ) : null}

        {/* Kosten und Empfehlungen */}
        <div className="grid gap-4 md:grid-cols-2">
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Kosten / Zeit</h3>
            <div className="space-y-2 text-sm text-gray-300">
              {costBand ? (
                <>
                  <p>
                    Bandbreite (indikativ):{" "}
                    <span className="text-white font-semibold">
                      {costBand.niedrig.toLocaleString("de-DE")} – {costBand.hoch.toLocaleString("de-DE")} EUR
                    </span>
                  </p>
                  <p>Basiswert: {costBand.basis.toLocaleString("de-DE")} EUR</p>
                  {costBand.confidence ? <p>Confidence: {costBand.confidence}%</p> : null}
                </>
              ) : (
                <p>
                  Indikation (einzelwert, unsicher): ca.{" "}
                  <span className="text-white font-semibold">
                    {result.kosten_indikation_eur.toLocaleString("de-DE")} EUR
                  </span>
                </p>
              )}
              <p>Kostenklasse: {result.kostenklasse}</p>
              <p>Bearbeitungszeit: ca. {result.geschaetzte_bearbeitungszeit_wochen} Wochen</p>
              <p>Netzausbau: {result.netzausbau_erforderlich ? "Ja" : "Nein"}</p>
            </div>
          </div>
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Empfehlungen</h3>
            <ul className="space-y-1 text-sm text-gray-300">
              {result.empfehlungen.map((e, i) => <li key={i} className="flex gap-2"><span className="text-blue-400">&#8226;</span>{e}</li>)}
            </ul>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Projektprofil & Hybridwirkung</h3>
            <div className="space-y-2 text-sm text-gray-300">
              <p>Installierte Gesamtleistung: <span className="text-white font-semibold">{fmt(result.projektprofil.total_installed_kw, 0)} kW</span></p>
              <p>Komponenten: {result.projektprofil.component_count}</p>
              <p>Hybridprojekt: {result.projektprofil.is_hybrid ? "Ja" : "Nein"}</p>
              <p>Max. Einspeisung am NAP: {fmt(result.projektprofil.max_export_kw, 0)} kW</p>
              <p>Max. Bezug am NAP: {fmt(result.projektprofil.max_import_kw, 0)} kW</p>
              <p className="text-gray-400">{result.projektprofil.summary}</p>
              {result.projektprofil.component_summary.length > 0 && (
                <ul className="space-y-1 text-xs text-gray-400">
                  {result.projektprofil.component_summary.map((item, index) => <li key={index}>{item}</li>)}
                </ul>
              )}
            </div>
          </div>
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Erweiterte Diagnose</h3>
            <div className="space-y-3 text-sm text-gray-300">
              <div>
                <div className="text-gray-400">Netzdienlichkeit</div>
                <div className="text-white font-semibold">{result.erweiterte_scores.netzdienlichkeit}/100</div>
              </div>
              <div>
                <div className="text-gray-400">Projektfit</div>
                <div className="text-white font-semibold">{result.erweiterte_scores.projektfit}/100</div>
              </div>
              <div>
                <div className="text-gray-400">Umwelt / Trasse</div>
                <div className="text-white font-semibold">{result.erweiterte_scores.umwelt_trasse}/100</div>
              </div>
              <div>
                <div className="text-gray-400">Stakeholder-Fit</div>
                <div className="text-white font-semibold">{result.erweiterte_scores.stakeholder_fit}/100</div>
              </div>
            </div>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Speicher / Flexibilitaet</h3>
            <div className="space-y-2 text-sm text-gray-300">
              <p>Relevant: {result.speicher_bewertung.relevant ? "Ja" : "Nein"}</p>
              <p>Betriebsart: {result.speicher_bewertung.operation_mode}</p>
              <p>Flex-Score: {result.speicher_bewertung.flexibility_score}/100</p>
              <p>Grid-Benefit-Score: {result.speicher_bewertung.grid_support_score}/100</p>
              <p className="text-gray-400">{result.speicher_bewertung.summary}</p>
              {result.speicher_bewertung.benefit_flags.length > 0 && (
                <ul className="text-xs text-gray-400 space-y-1">
                  {result.speicher_bewertung.benefit_flags.map((flag, index) => <li key={index}>{flag}</li>)}
                </ul>
              )}
            </div>
          </div>
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Umwelt / Trasse</h3>
            <div className="space-y-2 text-sm text-gray-300">
              <p>Risiko: {result.route_environment.risk_level}</p>
              <p>Score: {result.route_environment.risk_score}/100</p>
              <p className="text-gray-400">{result.route_environment.summary}</p>
              {result.route_environment.drivers.length > 0 && (
                <ul className="text-xs text-gray-400 space-y-1">
                  {result.route_environment.drivers.map((driver, index) => <li key={index}>{driver}</li>)}
                </ul>
              )}
            </div>
          </div>
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Stakeholder-Zielkonflikt</h3>
            <div className="space-y-2 text-sm text-gray-300">
              <p>Netzsicht: {result.stakeholder_bewertung.netzbetreiber_score}/100</p>
              <p>Projektsicht: {result.stakeholder_bewertung.projektierer_score}/100</p>
              <p>Umsetzbarkeit: {result.stakeholder_bewertung.umsetzung_score}/100</p>
              <p>Konfliktlevel: {result.stakeholder_bewertung.konflikt_level}</p>
              <p className="text-gray-400">{result.stakeholder_bewertung.konflikt_summary}</p>
              <p className="text-blue-300 text-xs">{result.stakeholder_bewertung.recommended_focus}</p>
            </div>
          </div>
        </div>

        <div className="grid md:grid-cols-2 gap-4">
          <div className={sectionClass}>
            <h3 className={sectionTitle}>KI-Lernprofil (unterstuetzend)</h3>
            <p className="mb-2 text-xs text-gray-500">
              Assoziative Einordnung aus historischem Feedback – ersetzt keine deterministische Normpruefung.
            </p>
            <div className="space-y-2 text-sm text-gray-300">
              <p>KI-Konfidenz: <span className="text-white font-semibold">{fmt(result.ki.konfidenz_prozent, 0)}%</span></p>
              <p>Aehnliche Faelle: {result.ki.aehnliche_faelle}</p>
              <p>Kalibrierung: {result.ki.kalibrierung.status} · Faktor {fmt(result.ki.kalibrierung.kalibrierungsfaktor, 2)}</p>
              <p>Feedback-Loop: {result.ki.feedback_loop.status} · Samples {result.ki.feedback_loop.samples_total}</p>
              <p>Bestaetigungsquote: {fmt(result.ki.feedback_loop.bestaetigungsquote * 100, 0)}%</p>
              <p>Verknuepfte Revisionen: {result.ki.feedback_loop.linked_samples}</p>
              <p className={result.ki.anomalie_check.is_anomaly ? "text-yellow-300" : "text-gray-400"}>
                Anomalie-Check: {result.ki.anomalie_check.summary || "Keine Auffaelligkeit erkannt."}
              </p>
              {result.ki.anomalie_check.flags.length > 0 && (
                <ul className="text-xs text-gray-400 space-y-1">
                  {result.ki.anomalie_check.flags.map((flag, index) => <li key={index}>{flag}</li>)}
                </ul>
              )}
            </div>
          </div>
          <div className={sectionClass}>
            <h3 className={sectionTitle}>KI-Hinweise</h3>
            <ul className="space-y-1 text-sm text-gray-300">
              {result.ki.hinweise.map((item, index) => <li key={index}>{item}</li>)}
            </ul>
            {result.revision?.hash ? (
              <p className="mt-3 text-xs text-gray-500 break-all">Revision-Hash: {result.revision.hash}</p>
            ) : null}
          </div>
        </div>

        {stakeholderPath === "vnb" && result.revision?.hash ? (
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Netzbetreiber-Feedback / Lernmodul</h3>
            <div className="grid md:grid-cols-3 gap-4">
              <div>
                <label className={labelClass}>Feedback-Typ</label>
                <select
                  className={selectClass}
                  value={feedbackType}
                  onChange={(e) => setFeedbackType(e.target.value as "bestaetigt" | "korrigiert")}
                >
                  <option value="bestaetigt">Ergebnis bestaetigen</option>
                  <option value="korrigiert">Ergebnis korrigieren</option>
                </select>
              </div>
              <div>
                <label className={labelClass}>KI-Entscheidung</label>
                <input className={inputClass} value={decisionFromResult(result)} readOnly />
              </div>
              <div>
                <label className={labelClass}>Finale VNB-Entscheidung</label>
                <select
                  className={selectClass}
                  value={feedbackType === "korrigiert" ? feedbackDecision : decisionFromResult(result)}
                  onChange={(e) => setFeedbackDecision(e.target.value as "A" | "B" | "C")}
                  disabled={feedbackType !== "korrigiert"}
                >
                  <option value="A">A</option>
                  <option value="B">B</option>
                  <option value="C">C</option>
                </select>
              </div>
            </div>
            <div className="mt-4">
              <label className={labelClass}>Kommentar / Begruendung</label>
              <textarea
                className={inputClass}
                rows={3}
                value={feedbackComment}
                onChange={(e) => setFeedbackComment(e.target.value)}
                placeholder="Z. B. warum das Ergebnis bestaetigt oder korrigiert wurde."
              />
            </div>
            <div className="mt-4 flex items-center justify-between gap-4">
              <p className="text-xs text-gray-400">
                Feedback wird revisionssicher mit Analyse-Hash verknuepft und in die Kalibrierung einbezogen.
              </p>
              <button
                onClick={handleKiFeedbackSubmit}
                disabled={isSubmittingFeedback}
                className="bg-brand-cyan text-black rounded p-2 px-4 font-semibold disabled:opacity-60"
              >
                {isSubmittingFeedback ? "Feedback wird gespeichert..." : "Feedback speichern"}
              </button>
            </div>
            {feedbackMessage ? <p className="mt-3 text-sm text-brand-cyan">{feedbackMessage}</p> : null}
          </div>
        ) : null}

        {showDeepTechnicalDetails ? (
          <div className={sectionClass}>
            <h3 className={sectionTitle}>Impedanzmodell</h3>
            <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
              <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Z Quelle</div><div className="text-white font-mono">{result.z_quelle_ohm} Ohm</div></div>
              <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Z Trafo</div><div className="text-white font-mono">{result.z_trafo_ohm} Ohm</div></div>
              <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Z Leitung</div><div className="text-white font-mono">{result.z_leitung_ohm} Ohm</div></div>
              <div className="bg-gray-900 rounded-lg p-3"><div className="text-gray-400 text-xs">Z Gesamt</div><div className="text-white font-mono">{result.z_gesamt_ohm} Ohm</div></div>
            </div>
          </div>
        ) : null}

        {/* Einschraenkungen */}
        {result.einschraenkungen.length > 0 && (
          <div className="bg-yellow-900/30 border border-yellow-700 rounded-xl p-4">
            <h4 className="text-yellow-400 font-semibold text-sm mb-2">Einschraenkungen</h4>
            <ul className="text-sm text-yellow-200 space-y-1">
              {result.einschraenkungen.map((e, i) => <li key={i}>{e}</li>)}
            </ul>
          </div>
        )}

        <div className={sectionClass}>
          <h3 className={sectionTitle}>Transparenz / Annahmen</h3>
          <div className="grid gap-4 text-sm md:grid-cols-3">
            <div>
              <h4 className="text-white font-medium mb-2">Annahmen</h4>
              <ul className="space-y-1 text-gray-300">
                {result.transparenz.assumptions.map((item, index) => <li key={index}>{item}</li>)}
              </ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-2">Confidence-Hinweise</h4>
              <ul className="space-y-1 text-gray-300">
                {result.transparenz.confidence_notes.map((item, index) => <li key={index}>{item}</li>)}
              </ul>
            </div>
            <div>
              <h4 className="text-white font-medium mb-2">Disclaimer</h4>
              <ul className="space-y-1 text-gray-300">
                {result.transparenz.disclaimers.map((item, index) => <li key={index}>{item}</li>)}
              </ul>
            </div>
          </div>
        </div>

        <AnalysisDisclaimer variant="compact" className="border-t border-gray-700 pt-4" />

        {/* Buttons */}
        <div className="flex flex-col gap-3 pt-4 sm:flex-row sm:items-center sm:justify-between">
          <button
            onClick={() => setStep(1)}
            className="rounded-xl border border-gray-600 px-5 py-2.5 text-sm text-gray-300 transition hover:text-white"
          >
            Eingaben bearbeiten
          </button>
          <div className="flex flex-col gap-3 sm:flex-row">
            <button
              onClick={resetWorkflow}
              className="rounded-xl border border-gray-600 px-5 py-2.5 text-sm text-gray-300 transition hover:text-white"
            >
              Neue Analyse
            </button>
            <button
              type="button"
              onClick={handlePdfExport}
              disabled={isExporting || !result || !authUser}
              className="rounded-xl bg-blue-600 px-6 py-2.5 text-sm font-semibold text-white transition hover:bg-blue-700 disabled:opacity-60"
            >
              {isExporting ? "Export laeuft..." : stakeholderCopy.exportLabel}
            </button>
          </div>
        </div>

        <div className="mt-6 border-t border-gray-700 pt-4 text-center text-gray-500 text-xs">
          Analyse-ID: {analysisRunId} | {new Date().toLocaleString("de-DE")} | Revisionssicher | Keine Gewaehr
        </div>
      </div>
    );
  }

  return null;
}

