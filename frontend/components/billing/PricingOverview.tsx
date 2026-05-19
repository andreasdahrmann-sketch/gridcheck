import Link from "next/link";
import { ArrowRight, CheckCircle2 } from "lucide-react";
import {
  EXPRESS_ADDON,
  PRICING_COMPARISON_ROWS,
  PUBLIC_PRICING_TIERS,
  type PublicPricingTier,
} from "@/lib/public-pricing";

function TierCard({ tier }: { tier: PublicPricingTier }) {
  return (
    <article
      className={`flex h-full flex-col rounded-[24px] border p-5 ${
        tier.featured
          ? "border-brand-cyan/35 bg-brand-cyan/10 shadow-[0_16px_48px_rgba(121,224,196,0.12)]"
          : "border-white/10 bg-black/10"
      }`}
    >
      <div>
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-brand-cyan">{tier.category}</p>
        <h3 className="mt-2 text-lg font-semibold text-white">{tier.name}</h3>
        {tier.priceNote ? <p className="mt-1 text-xs text-text-dim">{tier.priceNote}</p> : null}
        <p className="mt-3 text-2xl font-semibold tracking-tight text-white">{tier.price}</p>
      </div>
      <p className="mt-3 text-sm leading-6 text-text-muted">{tier.description}</p>
      <ul className="mt-4 flex-1 space-y-2">
        {tier.highlights.map((item) => (
          <li key={item} className="flex items-start gap-2 text-sm leading-6 text-white/90">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-brand-cyan" aria-hidden />
            <span>{item}</span>
          </li>
        ))}
      </ul>
      <Link
        href={tier.cta.href}
        className={`mt-5 inline-flex items-center justify-center rounded-xl px-4 py-2.5 text-sm font-semibold transition ${
          tier.featured
            ? "bg-brand-orange text-white hover:bg-brand-orangeHover"
            : "border border-white/15 text-white hover:bg-white/5"
        }`}
      >
        {tier.cta.label}
        <ArrowRight className="ml-2 h-4 w-4" />
      </Link>
    </article>
  );
}

export default function PricingOverview() {
  return (
    <div className="space-y-10">
      <div className="overflow-x-auto rounded-[24px] border border-white/10 bg-black/10">
        <table className="min-w-[880px] w-full border-collapse text-left text-sm">
          <thead>
            <tr className="border-b border-white/10">
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-[0.16em] text-text-dim">
                Merkmal
              </th>
              <th scope="col" className="px-4 py-3 font-semibold text-white">
                Free
              </th>
              <th scope="col" className="px-4 py-3 font-semibold text-white">
                Basic
              </th>
              <th scope="col" className="px-4 py-3 font-semibold text-brand-cyan">
                Premium
              </th>
              <th scope="col" className="px-4 py-3 font-semibold text-white">
                Pro
              </th>
              <th scope="col" className="px-4 py-3 font-semibold text-white">
                Professional
              </th>
              <th scope="col" className="px-4 py-3 font-semibold text-white">
                VNB Pilot
              </th>
            </tr>
          </thead>
          <tbody>
            {PRICING_COMPARISON_ROWS.map((row) => (
              <tr key={row.label} className="border-b border-white/5 last:border-0">
                <th scope="row" className="px-4 py-3 font-medium text-text-muted">
                  {row.label}
                </th>
                <td className="px-4 py-3 text-white/90">{row.free}</td>
                <td className="px-4 py-3 text-white/90">{row.basic}</td>
                <td className="px-4 py-3 text-white/90">{row.premium}</td>
                <td className="px-4 py-3 text-white/90">{row.pro}</td>
                <td className="px-4 py-3 text-white/90">{row.professional}</td>
                <td className="px-4 py-3 text-white/90">{row.pilot}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {PUBLIC_PRICING_TIERS.map((tier) => (
          <TierCard key={tier.id} tier={tier} />
        ))}
      </div>

      <aside className="rounded-[24px] border border-dashed border-white/15 bg-white/5 p-5">
        <p className="text-xs font-medium uppercase tracking-[0.18em] text-brand-cyan">Add-on</p>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <h3 className="text-lg font-semibold text-white">{EXPRESS_ADDON.name}</h3>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-text-muted">{EXPRESS_ADDON.description}</p>
          </div>
          <Link
            href="/contact?intent=express"
            className="inline-flex shrink-0 items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
          >
            Express anfragen
          </Link>
        </div>
      </aside>

      <p className="text-xs leading-5 text-text-dim">
        Alle Preise verstehen sich – sofern nicht anders angegeben – zzgl. gesetzlicher Umsatzsteuer. GridCheck liefert
        vorlaeufige Netzanschluss-Diagnostik, keine verbindliche Netzanschlusszusage.
      </p>
    </div>
  );
}
