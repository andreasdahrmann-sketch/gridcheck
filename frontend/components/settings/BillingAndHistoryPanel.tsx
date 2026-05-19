"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { Clock3, CreditCard, History, LockKeyholeOpen } from "lucide-react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import ProductDecisionGuide from "@/components/billing/ProductDecisionGuide";
import {
  createBillingCheckout,
  getBillingCheckoutSessionStatus,
  createBillingPortal,
  getBillingStatus,
  listAnalysisHistory,
  type AnalysisHistoryItem,
  type BillingOffer,
  type BillingStatus,
} from "@/lib/api/billing";
import {
  isSelfServeCheckoutPlan,
  normalizeCheckoutPlan,
  offerIdForCheckoutPlan,
} from "@/lib/billing-plans";
import {
  findOfferById,
  getOfferDisplayName,
  getOfferProfile,
  getPackageScopeLabel,
  getReportScopeLabel,
} from "@/lib/billing-product";
import {
  getBillingEventLabel,
  getBillingEventStatusLabel,
  getBillingEventSummary,
  getEntitlementStatusLabel,
  getRunStatusLabel,
  getServiceStatusLabel,
} from "@/lib/product-decision-guide";

type Notice =
  | {
      tone: "success" | "error";
      text: string;
    }
  | null;

function decisionLabel(code?: string | null) {
  if (code === "A") return "Machbar";
  if (code === "B") return "Bedingt machbar";
  if (code === "C") return "Kritisch";
  return "n/a";
}

function sourceLabel(source: string) {
  if (source === "project") return "Projekt";
  if (source === "legacy_persist") return "Legacy Persist";
  return "Direktcheck";
}

function billingLabel(status: BillingStatus) {
  if (status.subscription_state === "past_due") return "Zahlung offen";
  if (status.subscription_state === "checkout_pending") return "Sync ausstehend";
  if (status.subscription_state === "canceled") return "Beendet";
  if (status.has_active_subscription) return "Pro";
  if (status.has_prepaid_credits) return "Credits aktiv";
  return "Free";
}

function billingHeadline(status: BillingStatus) {
  if (status.subscription_state === "past_due") return "Pro Lizenz mit offenem Zahlungsstatus.";
  if (status.subscription_state === "checkout_pending") return "Pro Freischaltung wird bestaetigt.";
  if (status.subscription_state === "canceled") return "Pro Lizenz ist beendet.";
  if (status.subscription_state === "trialing") return "Pro Testphase ist aktiv.";
  if (status.has_active_subscription) return "Pro Lizenz ist aktiv.";
  if (status.has_prepaid_credits) {
    return `${status.active_paid_entitlements_count} aktives Paket mit verfuegbaren Credits gefunden.`;
  }
  return `${status.free_checks_remaining} von ${status.free_checks_limit} Free Checks verbleiben.`;
}

function secondaryBillingBadge(status: BillingStatus) {
  if (status.has_active_subscription) return "Laufende Lizenz";
  if (status.has_prepaid_credits) return `${status.active_paid_entitlements_count} aktive Paketrechte`;
  return `${status.free_checks_remaining} Free Checks offen`;
}

function billingSubline(status: BillingStatus) {
  if (status.billing_attention?.message) return status.billing_attention.message;
  if (status.has_active_subscription) return "Weitere Checks laufen ohne Freikontingentgrenze ueber die aktive SaaS-Lizenz.";
  if (status.has_prepaid_credits) {
    return "Bezahlte One-off-Pakete sind aktiv und koennen sofort fuer Analysen und Report-Scopes verwendet werden.";
  }
  return status.catalog.headline;
}

function categoryLabel(offer: BillingOffer) {
  if (offer.category === "saas") return "SaaS";
  if (offer.category === "pilot") return "Pilot";
  if (offer.category === "addon") return "Add-on";
  return "Pay-per-Use";
}

function readinessLabel(status: string) {
  if (status === "ready") return "bereit";
  if (status === "warning") return "mit Hinweisen";
  return "blockiert";
}

function contactHrefForOffer(offerId: string) {
  if (offerId === "vnb_pilot") return "/contact?intent=vnb-pilot";
  if (offerId === "express_upgrade") return "/contact?intent=express";
  if (offerId === "professional_anschlussstrategie") return "/contact?intent=professional";
  if (offerId === "pro_lizenz") return "/contact?intent=pro";
  return "/contact?intent=general";
}

export default function BillingAndHistoryPanel({ cardClass, isAdmin = false }: { cardClass: string; isAdmin?: boolean }) {
  const [notice, setNotice] = useState<Notice>(null);
  const [handledReturnKey, setHandledReturnKey] = useState<string | null>(null);
  const [handledCheckoutPlanKey, setHandledCheckoutPlanKey] = useState<string | null>(null);
  const queryClient = useQueryClient();
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  const billingQuery = useQuery<BillingStatus>({
    queryKey: ["billing-status"],
    queryFn: getBillingStatus,
  });

  const historyQuery = useQuery<AnalysisHistoryItem[]>({
    queryKey: ["analysis-history"],
    queryFn: () => listAnalysisHistory(20),
  });

  const checkoutMutation = useMutation({
    mutationFn: createBillingCheckout,
    onSuccess: (payload) => {
      window.location.href = payload.url;
    },
    onError: (err) => {
      setNotice({ tone: "error", text: err instanceof Error ? err.message : "Checkout konnte nicht gestartet werden." });
    },
  });

  const portalMutation = useMutation({
    mutationFn: createBillingPortal,
    onSuccess: (payload) => {
      window.location.href = payload.url;
    },
    onError: (err) => {
      setNotice({ tone: "error", text: err instanceof Error ? err.message : "Billing Portal konnte nicht gestartet werden." });
    },
  });

  const checkoutSessionMutation = useMutation({
    mutationFn: getBillingCheckoutSessionStatus,
    onSuccess: (payload) => {
      queryClient.setQueryData(["billing-status"], payload.billing);
      void queryClient.invalidateQueries({ queryKey: ["billing-status"] });
      void queryClient.invalidateQueries({ queryKey: ["analysis-history"] });

      if (payload.billing.subscription_state === "checkout_pending") {
        setNotice({
          tone: "success",
          text: "Checkout erkannt. Die finale Subscription-Freischaltung wird noch von Stripe bestaetigt.",
        });
      } else if (payload.synced) {
        setNotice({
          tone: "success",
          text: `${payload.offer_name ?? payload.offer_id ?? "Checkout"} wurde bestaetigt. Tarifstatus und Paketrechte sind aktualisiert.`,
        });
      } else if (payload.session_status === "complete") {
        setNotice({
          tone: "success",
          text: "Checkout abgeschlossen. Stripe meldet die finale Freischaltung noch, der Status wird aktualisiert.",
        });
      } else {
        setNotice({
          tone: "error",
          text: "Checkout-Rueckkehr erkannt, aber Stripe meldet noch keinen abgeschlossenen Zahlungsvorgang.",
        });
      }
      router.replace(pathname);
    },
    onError: (err) => {
      setNotice({
        tone: "error",
        text: err instanceof Error ? err.message : "Checkout-Status konnte nicht bestaetigt werden.",
      });
      router.replace(pathname);
    },
  });

  const historySummary = useMemo(() => {
    const items = historyQuery.data ?? [];
    const completed = items.filter((item) => item.status === "completed").length;
    return { total: items.length, completed };
  }, [historyQuery.data]);

  const recentAnalyses = useMemo(() => {
    const items = [...(historyQuery.data ?? [])];
    const rank = (status: string) => {
      if (status === "completed") return 0;
      if (status === "failed" || status === "validation_failed" || status === "engine_failed") return 2;
      return 1;
    };
    return items.sort((a, b) => {
      const byStatus = rank(a.status) - rank(b.status);
      if (byStatus !== 0) return byStatus;
      return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
    });
  }, [historyQuery.data]);

  function runStatusBadgeClass(status: string) {
    if (status === "completed") return "border-emerald-400/20 bg-emerald-500/10 text-emerald-200";
    if (status === "failed" || status === "validation_failed" || status === "engine_failed") {
      return "border-red-500/30 bg-red-500/10 text-red-300";
    }
    return "border-amber-300/20 bg-amber-300/10 text-amber-100";
  }

  useEffect(() => {
    const billingState = searchParams.get("billing");
    const sessionId = searchParams.get("session_id");
    if (!billingState) {
      return;
    }

    const returnKey = `${billingState}:${sessionId ?? ""}`;
    if (handledReturnKey === returnKey) {
      return;
    }
    setHandledReturnKey(returnKey);

    if (billingState === "cancel") {
      setNotice({ tone: "error", text: "Checkout wurde abgebrochen. Es wurden keine Paketrechte freigeschaltet." });
      router.replace(pathname);
      return;
    }

    if (billingState === "success") {
      if (sessionId) {
        checkoutSessionMutation.mutate(sessionId);
      } else {
        setNotice({
          tone: "success",
          text: "Checkout erfolgreich abgeschlossen. Tarifstatus wird aktualisiert.",
        });
        void queryClient.invalidateQueries({ queryKey: ["billing-status"] });
        router.replace(pathname);
      }
    }
  }, [checkoutSessionMutation, handledReturnKey, pathname, queryClient, router, searchParams]);

  useEffect(() => {
    const plan = normalizeCheckoutPlan(searchParams.get("plan"));
    const wantsCheckout = searchParams.get("checkout") === "1";
    if (!plan || !wantsCheckout || !isSelfServeCheckoutPlan(plan)) {
      return;
    }
    const offerId = offerIdForCheckoutPlan(plan);
    if (!offerId) {
      return;
    }
    const key = `${plan}:${offerId}`;
    if (handledCheckoutPlanKey === key || checkoutMutation.isPending) {
      return;
    }
    if (!billingQuery.isSuccess) {
      return;
    }
    const offer = billingQuery.data.catalog.offers.find((item) => item.offer_id === offerId);
    if (!offer?.checkout_enabled) {
      setNotice({
        tone: "error",
        text: "Stripe Checkout ist fuer dieses Paket in der aktuellen Umgebung nicht konfiguriert.",
      });
      router.replace(pathname);
      return;
    }
    setHandledCheckoutPlanKey(key);
    checkoutMutation.mutate(offerId);
  }, [
    billingQuery.data,
    billingQuery.isSuccess,
    checkoutMutation,
    handledCheckoutPlanKey,
    pathname,
    router,
    searchParams,
  ]);

  function startCheckout(offerId: string) {
    checkoutMutation.mutate(offerId);
  }

  return (
    <div className="space-y-6">
      <Card className={cardClass}>
        <CardHeader className="gap-3">
          <div className="flex items-center gap-3">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-brand-cyan">
              <CreditCard className="h-5 w-5" />
            </div>
            <div>
              <CardTitle className="text-white">Tarif & Analyse-History</CardTitle>
              <CardDescription className="text-text-muted">
                Launch-Pricing, Freemium-Gate und gespeicherte Check-Historie pro Benutzerkonto.
              </CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-5">
          {billingQuery.data?.billing_attention ? (
            <div
              className={`rounded-2xl border px-4 py-4 text-sm ${
                billingQuery.data.billing_attention.severity === "warning"
                  ? "border-amber-300/30 bg-amber-300/10 text-amber-100"
                  : "border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan"
              }`}
            >
              <p className="font-medium text-white">{billingQuery.data.billing_attention.title}</p>
              <p className="mt-2 leading-6">{billingQuery.data.billing_attention.message}</p>
              {billingQuery.data.billing_attention.action === "open_portal" ? (
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => portalMutation.mutate()}
                  disabled={!billingQuery.data.customer_portal_available || portalMutation.isPending}
                  className="mt-3 h-10 rounded-xl border-white/15 bg-transparent text-white hover:bg-white/5"
                >
                  <CreditCard className="mr-2 h-4 w-4" />
                  {portalMutation.isPending
                    ? "Portal startet..."
                    : billingQuery.data.billing_attention.cta_label ?? "Billing Portal oeffnen"}
                </Button>
              ) : null}
            </div>
          ) : null}

          {notice ? (
            <div
              className={`rounded-2xl border px-4 py-3 text-sm ${
                notice.tone === "success"
                  ? "border-brand-cyan/30 bg-brand-cyan/10 text-brand-cyan"
                  : "border-red-500/30 bg-red-500/10 text-red-300"
              }`}
            >
              {notice.text}
            </div>
          ) : null}

          {billingQuery.isLoading ? (
            <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-sm text-text-muted">
              Tarifstatus wird geladen...
            </div>
          ) : billingQuery.isError || !billingQuery.data ? (
            <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-4 text-sm text-red-300">
              Tarifstatus konnte nicht geladen werden.
            </div>
          ) : (
            <>
              {isAdmin ? (
                <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                  <div className="flex flex-wrap items-center justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-white">Stripe-Readiness</p>
                      <p className="mt-1 text-sm text-text-muted">
                        Operativer Check fuer Checkout, Webhook, Portal und die direkt buchbaren Self-Serve-Angebote.
                      </p>
                    </div>
                    <span
                      className={`rounded-full border px-3 py-1 text-[11px] uppercase tracking-[0.14em] ${
                        billingQuery.data.stripe_readiness.status === "ready"
                          ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
                          : billingQuery.data.stripe_readiness.status === "warning"
                            ? "border-amber-300/20 bg-amber-300/10 text-amber-100"
                            : "border-red-500/30 bg-red-500/10 text-red-300"
                      }`}
                    >
                      {readinessLabel(billingQuery.data.stripe_readiness.status)}
                    </span>
                  </div>

                  <div className="mt-4 grid gap-3 md:grid-cols-3">
                    <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.14em] text-text-dim">Checkout</p>
                      <p className="mt-2 text-sm text-white">
                        {billingQuery.data.stripe_readiness.checkout_ready ? "bereit" : "nicht bereit"}
                      </p>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.14em] text-text-dim">Webhook</p>
                      <p className="mt-2 text-sm text-white">
                        {billingQuery.data.stripe_readiness.webhook_ready ? "bereit" : "nicht bereit"}
                      </p>
                    </div>
                    <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                      <p className="text-xs uppercase tracking-[0.14em] text-text-dim">Portal</p>
                      <p className="mt-2 text-sm text-white">
                        {billingQuery.data.stripe_readiness.portal_ready ? "bereit" : "nicht bereit"}
                      </p>
                    </div>
                  </div>

                  {billingQuery.data.stripe_readiness.issues.length > 0 ? (
                    <div className="mt-4 rounded-xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                      <p className="font-medium text-white">Blocker</p>
                      <div className="mt-2 space-y-1">
                        {billingQuery.data.stripe_readiness.issues.map((issue) => (
                          <p key={issue}>{issue}</p>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  {billingQuery.data.stripe_readiness.warnings.length > 0 ? (
                    <div className="mt-4 rounded-xl border border-amber-300/20 bg-amber-300/10 px-4 py-3 text-sm text-amber-100">
                      <p className="font-medium text-white">Hinweise</p>
                      <div className="mt-2 space-y-1">
                        {billingQuery.data.stripe_readiness.warnings.map((warning) => (
                          <p key={warning}>{warning}</p>
                        ))}
                      </div>
                    </div>
                  ) : null}

                  <div className="mt-4 grid gap-3 lg:grid-cols-2">
                    {billingQuery.data.stripe_readiness.offers
                      .filter((offer) => offer.billing_mode !== "addon")
                      .map((offer) => (
                        <div key={offer.offer_id} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                          <div className="flex items-start justify-between gap-3">
                            <p className="text-sm font-medium text-white">{getOfferDisplayName(offer.offer_id)}</p>
                            <span
                              className={`rounded-full border px-3 py-1 text-[11px] ${
                                offer.ready
                                  ? "border-emerald-400/20 bg-emerald-500/10 text-emerald-200"
                                  : "border-red-500/30 bg-red-500/10 text-red-300"
                              }`}
                            >
                              {offer.ready ? "bereit" : "fehlt"}
                            </span>
                          </div>
                          <p className="mt-2 text-xs text-text-muted">
                            {offer.billing_mode === "subscription" ? "Subscription" : "Einzelkauf"}
                          </p>
                          {offer.issues.length > 0 ? (
                            <div className="mt-2 space-y-1 text-xs text-text-dim">
                              {offer.issues.map((issue) => (
                                <p key={`${offer.offer_id}-${issue}`}>{issue}</p>
                              ))}
                            </div>
                          ) : null}
                        </div>
                      ))}
                  </div>
                  <p className="mt-3 text-xs text-text-dim">
                    Express bleibt hier bewusst ausserhalb der Pflicht-Readiness, weil der MVP ihn als Kontakt-/OPS-Pfad fuehrt.
                  </p>
                </div>
              ) : null}

              <div className="grid gap-4 md:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-3 py-1 text-xs font-medium text-brand-cyan">
                      {billingLabel(billingQuery.data)}
                    </span>
                    <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-white">
                      {secondaryBillingBadge(billingQuery.data)}
                    </span>
                  </div>
                  <p className="mt-3 text-lg font-semibold text-white">
                    {billingHeadline(billingQuery.data)}
                  </p>
                  <p className="mt-2 text-sm leading-6 text-text-muted">
                    {billingSubline(billingQuery.data)}
                  </p>
                  {billingQuery.data.current_period_end ? (
                    <p className="mt-2 text-xs text-text-dim">
                      Aktuelle Periode bis {new Date(billingQuery.data.current_period_end).toLocaleDateString("de-DE")}
                    </p>
                  ) : null}
                  {billingQuery.data.has_ops_pending ? (
                    <p className="mt-2 text-xs text-amber-200">
                      Betreute Nachbearbeitung offen: mindestens ein Paket wartet auf den naechsten Service-Schritt.
                    </p>
                  ) : null}
                </div>

                <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                  <div className="text-xs uppercase tracking-[0.2em] text-text-dim">Nutzung</div>
                  <dl className="mt-3 space-y-3 text-sm">
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-text-dim">Verbrauchte Free Checks</dt>
                      <dd className="text-right text-white">{billingQuery.data.free_checks_used}</dd>
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-text-dim">Analysen in History</dt>
                      <dd className="text-right text-white">{historySummary.total}</dd>
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-text-dim">Erfolgreiche Runs</dt>
                      <dd className="text-right text-white">{historySummary.completed}</dd>
                    </div>
                    <div className="flex items-start justify-between gap-3">
                      <dt className="text-text-dim">Offene Service-Nachlaeufe</dt>
                      <dd className="text-right text-white">{billingQuery.data.open_ops_followups_count}</dd>
                    </div>
                  </dl>
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                <p className="text-sm font-medium text-white">Produktlogik im MVP</p>
                <div className="mt-3 grid gap-3 lg:grid-cols-3">
                  <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-text-dim">Self-Serve</p>
                    <p className="mt-2 text-sm text-white">Free, Basic, Premium und Pro decken den eigenstaendigen Analysepfad ab.</p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-text-dim">Servicepfad</p>
                    <p className="mt-2 text-sm text-white">
                      Professional erweitert den Reportscope und markiert den Fall fuer betreute Nachbearbeitung.
                    </p>
                  </div>
                  <div className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                    <p className="text-xs uppercase tracking-[0.14em] text-text-dim">Pilot & Add-on</p>
                    <p className="mt-2 text-sm text-white">
                      Express bleibt ein Zeit-Zusatz, VNB Pilot ein abgestimmter Kontakt- und Pilotpfad.
                    </p>
                  </div>
                </div>
              </div>

              <ProductDecisionGuide
                title="Entscheidungshilfe fuer Tarif und Servicepfad"
                description="Diese Hilfestellung uebersetzt Paketgrenzen in kaufbare Entscheidungen: Wann reicht Self-Serve, wann passt Pro besser und wann beginnt bewusst ein betreuter Service- oder Pilotpfad."
                currentOfferId={
                  billingQuery.data.has_active_subscription
                    ? "pro_lizenz"
                    : billingQuery.data.active_entitlements[0]?.offer_id ?? "free"
                }
                currentPackageScope={
                  billingQuery.data.has_active_subscription
                    ? "premium"
                    : billingQuery.data.active_entitlements[0]?.package_scope ?? "basic"
                }
                compact
              />

              {billingQuery.data.active_entitlements.length > 0 ? (
                <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                  <p className="text-sm font-medium text-white">Aktive Paketrechte & Credits</p>
                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                    {billingQuery.data.active_entitlements.map((entitlement) => {
                      const offer = findOfferById(
                        billingQuery.data.catalog.offers,
                        billingQuery.data.catalog.addons,
                        entitlement.offer_id,
                      );
                      const profile = getOfferProfile(entitlement.offer_id, entitlement.package_scope);
                      return (
                        <div key={entitlement.id} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-sm font-semibold text-white">
                                {offer?.name ?? getOfferDisplayName(entitlement.offer_id)}
                              </p>
                              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-text-dim">
                                {getPackageScopeLabel(entitlement.package_scope)} · {profile.badge}
                              </p>
                            </div>
                            <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] text-white">
                              {entitlement.remaining_credits ?? "laufend"}
                            </span>
                          </div>
                          <p className="mt-3 text-xs leading-5 text-text-muted">{profile.deliverable}</p>
                          <p className="mt-2 text-xs text-text-muted">
                            Status {getEntitlementStatusLabel(entitlement.status)} · Service{" "}
                            {getServiceStatusLabel(entitlement.ops_status)}
                          </p>
                          {entitlement.valid_until ? (
                            <p className="mt-1 text-xs text-text-dim">
                              Gueltig bis {new Date(entitlement.valid_until).toLocaleDateString("de-DE")}
                            </p>
                          ) : null}
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {billingQuery.data.entitlement_history.filter(
                (item) => !billingQuery.data.active_entitlements.some((active) => active.id === item.id)
              ).length > 0 ? (
                <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                  <p className="text-sm font-medium text-white">Paketverlauf & Verbrauch</p>
                  <p className="mt-1 text-sm text-text-muted">
                    Bereits gekaufte oder verbrauchte Angebote bleiben fuer Abrechnung, Nachvollziehbarkeit und Support sichtbar.
                  </p>
                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                    {billingQuery.data.entitlement_history
                      .filter((item) => !billingQuery.data.active_entitlements.some((active) => active.id === item.id))
                      .map((entitlement) => {
                        const offer = findOfferById(
                          billingQuery.data.catalog.offers,
                          billingQuery.data.catalog.addons,
                          entitlement.offer_id,
                        );
                        const profile = getOfferProfile(entitlement.offer_id, entitlement.package_scope);
                        return (
                          <div key={entitlement.id} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <p className="text-sm font-semibold text-white">
                                  {offer?.name ?? getOfferDisplayName(entitlement.offer_id)}
                                </p>
                                <p className="mt-1 text-xs uppercase tracking-[0.14em] text-text-dim">
                                  {getPackageScopeLabel(entitlement.package_scope)} · Status{" "}
                                  {getEntitlementStatusLabel(entitlement.status)}
                                </p>
                              </div>
                              <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] text-white">
                                {entitlement.remaining_credits ?? "laufend"}
                              </span>
                            </div>
                            <p className="mt-3 text-xs leading-5 text-text-muted">{profile.deliverable}</p>
                            {entitlement.last_analysis_project_name ? (
                              <p className="mt-2 text-xs text-text-muted">
                                Letzte Nutzung: Projekt {entitlement.last_analysis_project_name}
                              </p>
                            ) : null}
                            {entitlement.last_analysis_created_at ? (
                              <p className="mt-1 text-xs text-text-dim">
                                Letzter Analysebezug {new Date(entitlement.last_analysis_created_at).toLocaleString("de-DE")}
                              </p>
                            ) : null}
                            {entitlement.valid_until ? (
                              <p className="mt-1 text-xs text-text-dim">
                                Gueltig bis {new Date(entitlement.valid_until).toLocaleDateString("de-DE")}
                              </p>
                            ) : null}
                          </div>
                        );
                      })}
                  </div>
                </div>
              ) : null}

              {billingQuery.data.ops_followups.length > 0 ? (
                <div className="rounded-2xl border border-amber-400/20 bg-amber-500/5 px-4 py-4">
                  <p className="text-sm font-medium text-white">Betreute Nachlaeufe</p>
                  <p className="mt-1 text-sm text-text-muted">
                    Professional und Express bleiben sichtbar im betreuten Nachlauf und werden nicht nur als bezahltes Paket
                    abgelegt.
                  </p>
                  <div className="mt-3 grid gap-3 lg:grid-cols-2">
                    {billingQuery.data.ops_followups.map((followup) => {
                      const offer = findOfferById(
                        billingQuery.data.catalog.offers,
                        billingQuery.data.catalog.addons,
                        followup.offer_id,
                      );
                      const profile = getOfferProfile(followup.offer_id, followup.package_scope);
                      return (
                        <div key={followup.entitlement_id} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="text-sm font-semibold text-white">
                                {offer?.name ?? getOfferDisplayName(followup.offer_id)}
                              </p>
                              <p className="mt-1 text-xs uppercase tracking-[0.14em] text-text-dim">
                                {getPackageScopeLabel(followup.package_scope)} · Service{" "}
                                {getServiceStatusLabel(followup.ops_status)}
                              </p>
                            </div>
                            <span className="rounded-full border border-amber-300/20 bg-amber-300/10 px-3 py-1 text-[11px] text-amber-100">
                              offen
                            </span>
                          </div>
                          <p className="mt-3 text-xs leading-5 text-text-muted">{profile.deliverable}</p>
                          {followup.project_name ? (
                            <p className="mt-3 text-xs text-text-muted">Projekt {followup.project_name}</p>
                          ) : null}
                          <p className="mt-2 text-sm text-white">{followup.next_action}</p>
                          <div className="mt-3 flex flex-col gap-1 text-xs text-text-dim">
                            {followup.analysis_created_at ? (
                              <span>Letzter Analysebezug {new Date(followup.analysis_created_at).toLocaleString("de-DE")}</span>
                            ) : null}
                            {followup.updated_at ? (
                              <span>Zuletzt aktualisiert {new Date(followup.updated_at).toLocaleString("de-DE")}</span>
                            ) : null}
                            {followup.checkout_session_id ? <span>Session {followup.checkout_session_id}</span> : null}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>
              ) : null}

              {billingQuery.data.recent_billing_events.length > 0 ? (
                <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                  <p className="text-sm font-medium text-white">Letzte Aktivierungen & Abrechnungsereignisse</p>
                  <div className="mt-3 space-y-3">
                    {billingQuery.data.recent_billing_events.map((event) => (
                      <div key={event.id} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                        <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <p className="text-sm font-semibold text-white">{getBillingEventLabel(event.event_type)}</p>
                            <p className="mt-1 text-xs text-text-muted">
                              Status {getBillingEventStatusLabel(event.status)}
                              {event.checkout_session_id ? ` · Session ${event.checkout_session_id}` : ""}
                            </p>
                          </div>
                          <div className="text-left text-xs text-text-dim sm:text-right">
                            {event.created_at ? new Date(event.created_at).toLocaleString("de-DE") : "Zeitpunkt offen"}
                          </div>
                        </div>
                        {(event.amount_cents ?? null) !== null ? (
                          <p className="mt-2 text-xs text-text-dim">
                            Betrag {(event.amount_cents ?? 0) / 100} {(event.currency ?? "eur").toUpperCase()}
                          </p>
                        ) : null}
                        <p className="mt-2 text-xs leading-5 text-text-muted">
                          {getBillingEventSummary(event.event_type, event.status)}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                <p className="text-sm font-medium text-white">Buchbarkeit & Aktivierung</p>
                <div className="mt-3 space-y-2 text-sm text-text-muted">
                  <p>
                    Self-Serve-Angebote werden nach erfolgreichem Checkout direkt dem Konto zugeordnet. Service- und
                    Pilotpfade bleiben bewusst kontakt- oder projektbasiert.
                  </p>
                  <p>
                    Subscription und gekaufte Credits erscheinen nach erfolgreicher Aktivierung in den Paketrechten und
                    werden anschliessend in History, Projekten und Follow-ups sichtbar.
                  </p>
                </div>
                <div className="mt-4 grid gap-3 lg:grid-cols-2">
                  {billingQuery.data.catalog.offers.map((offer) => (
                    <div key={offer.offer_id} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-medium text-white">{offer.name}</p>
                          <p className="mt-1 text-xs uppercase tracking-[0.14em] text-text-dim">{categoryLabel(offer)}</p>
                        </div>
                        <span
                          className={`rounded-full border px-3 py-1 text-[11px] ${
                            offer.billing_mode === "contact"
                              ? "border-white/10 bg-black/20 text-white"
                              : offer.checkout_enabled
                              ? "border-brand-cyan/20 bg-brand-cyan/10 text-brand-cyan"
                              : "border-red-500/30 bg-red-500/10 text-red-300"
                          }`}
                        >
                          {offer.billing_mode === "contact"
                            ? "kontaktbasiert"
                            : offer.checkout_enabled
                              ? "direkt buchbar"
                              : "derzeit nicht direkt buchbar"}
                        </span>
                      </div>
                      <p className="mt-3 text-xs leading-5 text-text-muted">{offer.summary}</p>
                      <p className="mt-2 text-xs leading-5 text-text-dim">
                        {offer.billing_mode === "contact"
                          ? "Dieser Pfad wird bewusst nicht als normaler Self-Serve-Checkout gefuehrt."
                          : offer.checkout_enabled
                            ? "Nach erfolgreichem Checkout werden Rechte, Credits oder Subscription-Status automatisch aktualisiert."
                            : "Dieser Pfad ist in der aktuellen Umgebung nicht direkt self-serve aktivierbar."}
                      </p>
                    </div>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl border border-white/10 bg-black/10 px-4 py-4">
                <p className="text-sm font-medium text-white">Usage-Logik</p>
                <div className="mt-3 space-y-2 text-sm text-text-muted">
                  <p>{billingQuery.data.usage_policy.free_checks.consumption_rule}</p>
                  <p>{billingQuery.data.usage_policy.pay_per_use.consumption_rule}</p>
                  <p>{billingQuery.data.usage_policy.subscription.consumption_rule}</p>
                  <p>{billingQuery.data.usage_policy.ops_boundary.professional}</p>
                  <p>{billingQuery.data.usage_policy.ops_boundary.express}</p>
                </div>
              </div>

              <div className="grid gap-3 xl:grid-cols-2">
                {billingQuery.data.catalog.offers.map((offer) => {
                  const isContactOnly = offer.billing_mode === "contact";
                  return (
                    <div
                      key={offer.offer_id}
                      className={`rounded-2xl border p-4 ${
                        offer.featured ? "border-brand-cyan/35 bg-brand-cyan/10" : "border-white/10 bg-black/10"
                      }`}
                    >
                      <div className="flex items-start justify-between gap-3">
                        <div>
                          <p className="text-sm font-semibold text-white">{offer.name}</p>
                          <p className="mt-1 text-lg font-semibold text-white">{offer.price_label}</p>
                        </div>
                        <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-gray-300">
                          {categoryLabel(offer)}
                        </span>
                      </div>
                      <p className="mt-3 text-sm text-gray-200">{offer.tagline}</p>
                      <p className="mt-2 text-sm text-gray-400">{offer.summary}</p>
                      <p className="mt-3 text-xs text-gray-400">Ideal fuer: {offer.recommended_for}</p>
                      <div className="mt-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                        {isContactOnly ? (
                          <Link
                            href={contactHrefForOffer(offer.offer_id)}
                            className="inline-flex items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
                          >
                            {offer.cta_label}
                          </Link>
                        ) : (
                          <Button
                            type="button"
                            onClick={() => startCheckout(offer.offer_id)}
                            disabled={!offer.checkout_enabled || checkoutMutation.isPending}
                            className={`h-11 rounded-xl px-5 ${
                              offer.offer_id === "pro_lizenz"
                                ? "bg-brand-cyan text-black hover:bg-brand-cyan/90"
                                : "bg-brand-orange text-white hover:bg-brand-orangeHover"
                            }`}
                          >
                            <LockKeyholeOpen className="mr-2 h-4 w-4" />
                            {checkoutMutation.isPending ? "Checkout startet..." : offer.cta_label}
                          </Button>
                        )}
                        <span className={`text-xs ${offer.self_serve_unlock ? "text-brand-cyan" : "text-text-dim"}`}>
                          {offer.self_serve_unlock ? "Self-Serve Unlock" : "Service-/Projektpfad"}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>

              {billingQuery.data.catalog.addons.length > 0 ? (
                <div className="rounded-2xl border border-dashed border-white/15 bg-black/10 px-4 py-4">
                  <p className="text-sm font-medium text-white">Sichtbar vorbereitete Add-ons</p>
                  <div className="mt-3 flex flex-wrap gap-3">
                    {billingQuery.data.catalog.addons.map((offer) => (
                      <div key={offer.offer_id} className="rounded-xl border border-white/10 bg-white/5 px-4 py-3">
                        <p className="text-sm font-medium text-white">{offer.name}</p>
                        <p className="mt-1 text-xs text-text-muted">{offer.tagline}</p>
                        <Link
                          href={contactHrefForOffer(offer.offer_id)}
                          className="mt-3 inline-flex items-center justify-center rounded-lg border border-white/15 px-3 py-2 text-xs font-semibold text-white transition hover:bg-white/5"
                        >
                          Zusatzpfad anfragen
                        </Link>
                      </div>
                    ))}
                  </div>
                </div>
              ) : null}

              <div className="flex flex-col gap-3 sm:flex-row">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => portalMutation.mutate()}
                  disabled={!billingQuery.data.customer_portal_available || portalMutation.isPending}
                  className="h-11 rounded-xl border-border/70 bg-transparent text-white hover:bg-white/5"
                >
                  <CreditCard className="mr-2 h-4 w-4" />
                  {portalMutation.isPending ? "Portal startet..." : "Subscription verwalten"}
                </Button>
              </div>
            </>
          )}

          <Separator className="bg-white/10" />

          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-2xl border border-white/10 bg-white/5 text-brand-mint">
                <History className="h-4 w-4" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">Analyse-History</p>
                <p className="text-sm text-text-muted">
                  Jeder Run wird kontobezogen gespeichert. Erfolgreiche Checks verbrauchen das Free-Kontingent.
                </p>
              </div>
            </div>

            {historyQuery.isLoading ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4 text-sm text-text-muted">
                History wird geladen...
              </div>
            ) : historyQuery.isError ? (
              <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-4 text-sm text-red-300">
                Analyse-History konnte nicht geladen werden.
              </div>
            ) : recentAnalyses.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-6 text-sm text-text-muted">
                Noch keine gespeicherten Analysen vorhanden.
              </div>
            ) : (
              <div className="space-y-3">
                {recentAnalyses.map((item) => {
                  const offer = findOfferById(
                    billingQuery.data?.catalog.offers,
                    billingQuery.data?.catalog.addons,
                    item.offer_id,
                  );
                  const profile = getOfferProfile(item.offer_id, item.package_scope);
                  return (
                    <div key={item.id} className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                      <div className="flex flex-col gap-3 lg:flex-row lg:items-start lg:justify-between">
                        <div className="min-w-0">
                          <div className="flex flex-wrap items-center gap-2">
                            <span
                              className={`rounded-full border px-3 py-1 text-xs ${runStatusBadgeClass(item.status)}`}
                            >
                              {getRunStatusLabel(item.status)}
                            </span>
                            <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-white">
                              Run #{item.id}
                            </span>
                            <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-white">
                              {sourceLabel(item.source)}
                            </span>
                            <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-white">
                              {item.billing_category === "paid"
                                ? "Bezahlter Run"
                                : item.free_quota_consumed
                                  ? "Free Check"
                                  : "Ohne Kontingent"}
                            </span>
                            <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-white">
                              {getPackageScopeLabel(item.package_scope)}
                            </span>
                            <span className="rounded-full border border-white/10 bg-black/20 px-3 py-1 text-xs text-white">
                              {offer?.name ?? getOfferDisplayName(item.offer_id)}
                            </span>
                          </div>
                          <p className="mt-3 text-sm font-medium text-white">
                            {item.project_id ? (
                              <Link href={`/projects/${item.project_id}`} className="hover:text-brand-cyan">
                                {item.project_name || `Projekt ${item.project_id}`}
                              </Link>
                            ) : (
                              "Direkt aus dem Check gestartet"
                            )}
                          </p>
                          <p className="mt-1 text-sm text-text-muted">
                            Status {getRunStatusLabel(item.status)} · Entscheidung {decisionLabel(item.decision_code)} · Score{" "}
                            {typeof item.score === "number" ? `${Math.round(item.score)}/100` : "n/a"}
                          </p>
                          <p className="mt-2 text-xs leading-5 text-text-muted">{profile.deliverable}</p>
                          <p className="mt-1 text-xs leading-5 text-text-dim">{profile.boundary}</p>
                        </div>
                        <div className="text-sm text-text-muted">
                          <div className="flex items-center gap-2">
                            <Clock3 className="h-4 w-4" />
                            {new Date(item.created_at).toLocaleString("de-DE")}
                          </div>
                          <p className="mt-2 text-xs text-text-dim">Reporttiefe {getReportScopeLabel(item.package_scope)}</p>
                          {item.revision_hash ? (
                            <p className="mt-2 max-w-[280px] break-all text-xs text-text-dim">{item.revision_hash}</p>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
