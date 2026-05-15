"use client";

import Link from "next/link";
import { useEffect } from "react";
import { trackConversionEvent } from "@/lib/api/analytics";
import {
  DECISION_GUIDE_CARDS,
  PRODUCT_FAQS,
  getNextStepGuidance,
} from "@/lib/product-decision-guide";

export default function ProductDecisionGuide({
  title = "Welche Option passt wann?",
  description = "Die Produktpfade bleiben bewusst getrennt, damit Scope, Nutzen und naechster Schritt kaufbar und nachvollziehbar bleiben.",
  currentOfferId,
  currentPackageScope,
  compact = false,
}: {
  title?: string;
  description?: string;
  currentOfferId?: string | null;
  currentPackageScope?: string | null;
  compact?: boolean;
}) {
  const nextStep = getNextStepGuidance(currentOfferId, currentPackageScope);

  useEffect(() => {
    void trackConversionEvent("page_view_product", {
      surface: compact ? "compact" : "full",
      current_offer_id: currentOfferId ?? null,
      current_package_scope: currentPackageScope ?? null,
    });
  }, [compact, currentOfferId, currentPackageScope]);

  return (
    <section className="space-y-4 rounded-[28px] border border-white/10 bg-white/5 p-5">
      <div>
        <div className="text-xs font-medium uppercase tracking-[0.22em] text-brand-cyan">Paketwahl-Hilfe</div>
        <h2 className="mt-3 text-2xl font-semibold text-white">{title}</h2>
        <p className="mt-2 max-w-3xl text-sm leading-6 text-text-muted">{description}</p>
      </div>

      <div className={`grid gap-3 ${compact ? "lg:grid-cols-2" : "xl:grid-cols-5 md:grid-cols-2"}`}>
        {DECISION_GUIDE_CARDS.map((card) => (
          <div key={card.id} className="rounded-2xl border border-white/10 bg-black/10 p-4">
            <div className="inline-flex rounded-full border border-white/10 bg-black/20 px-3 py-1 text-[11px] uppercase tracking-[0.14em] text-white">
              {card.badge}
            </div>
            <p className="mt-3 text-sm font-semibold text-white">{card.title}</p>
            <p className="mt-2 text-xs leading-5 text-text-muted">{card.whenToChoose}</p>
            <p className="mt-2 text-xs leading-5 text-white/85">{card.included}</p>
            <p className="mt-2 text-xs leading-5 text-text-dim">{card.notFor}</p>
            <Link
              href={card.href}
              className="mt-4 inline-flex items-center justify-center rounded-xl border border-white/15 px-3 py-2 text-xs font-semibold text-white transition hover:bg-white/5"
            >
              {card.cta}
            </Link>
          </div>
        ))}
      </div>

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1.1fr)_minmax(320px,0.9fr)]">
        <div className="rounded-2xl border border-white/10 bg-black/10 p-4">
          <p className="text-sm font-medium text-white">Haeufige Fragen zur Paketwahl</p>
          <div className="mt-3 grid gap-3 md:grid-cols-2">
            {PRODUCT_FAQS.map((faq) => (
              <div key={faq.question} className="rounded-xl border border-white/10 bg-white/5 p-3">
                <p className="text-sm font-semibold text-white">{faq.question}</p>
                <p className="mt-2 text-xs leading-5 text-text-muted">{faq.answer}</p>
              </div>
            ))}
          </div>
        </div>

        <div className="rounded-2xl border border-brand-cyan/20 bg-brand-cyan/10 p-4">
          <p className="text-sm font-medium text-white">Naechste Entscheidung</p>
          <p className="mt-3 text-base font-semibold text-white">{nextStep.title}</p>
          <p className="mt-2 text-sm leading-6 text-white/85">{nextStep.summary}</p>
          <div className="mt-4 flex flex-col gap-2">
            {nextStep.actions.map((action) => (
              <Link
                key={`${action.label}-${action.href}`}
                href={action.href}
                className="inline-flex items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
              >
                {action.label}
              </Link>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
