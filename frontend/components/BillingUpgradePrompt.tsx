"use client";

import Link from "next/link";
import type { BillingOffer, BillingStatus } from "@/lib/api/billing";
import { findOfferById, getOfferProfile } from "@/lib/billing-product";

function recommendedOffers(status: BillingStatus): BillingOffer[] {
  const offers = status.catalog.offers ?? [];
  const ids = status.recommended_offer_ids ?? [];
  const picked = ids
    .map((offerId) => offers.find((offer) => offer.offer_id === offerId))
    .filter((offer): offer is BillingOffer => Boolean(offer));
  return picked.length > 0 ? picked : offers.filter((offer) => offer.checkout_enabled).slice(0, 3);
}

export default function BillingUpgradePrompt({
  billing,
  onCheckout,
  isStartingCheckout = false,
  compact = false,
}: {
  billing: BillingStatus | null | undefined;
  onCheckout: (offerId: string) => void;
  isStartingCheckout?: boolean;
  compact?: boolean;
}) {
  if (!billing || !billing.upgrade_required) {
    return null;
  }

  const offers = recommendedOffers(billing);
  const pilotOffer = findOfferById(billing.catalog.offers, billing.catalog.addons, "vnb_pilot");
  const expressOffer = findOfferById(billing.catalog.offers, billing.catalog.addons, "express_upgrade");
  const isPastDue = billing.subscription_state === "past_due";
  const headline = isPastDue ? "Pro Zahlung offen - neue Subscription-Analysen gesperrt" : "Upgrade fuer weitere Analysen erforderlich";
  const intro = isPastDue
    ? "Die laufende Pro-Subscription ist wegen offener Zahlung aktuell nicht fuer neue Analysen nutzbar. Billing-Portal, Projekte, History und bestehende Reports bleiben offen; separat bezahlte One-off-Pakete koennen weiterhin verwendet werden."
    : `${billing.free_checks_used} von ${billing.free_checks_limit} Free Checks wurden bereits verbraucht. Fuer weitere Analysen ist jetzt ein klares Produktpaket noetig: Self-Serve fuer einzelne Projekte, Pro fuer laufende Pipeline oder Pilot-/Servicepfade fuer abgestimmte Faelle.`;

  return (
    <div className={`rounded-2xl border border-brand-orange/30 bg-brand-orange/10 ${compact ? "p-4" : "p-5"}`}>
      <p className="text-sm font-semibold text-white">{headline}</p>
      <p className="mt-2 text-sm leading-6 text-gray-200">{intro}</p>
      <div className={`mt-4 grid gap-3 ${compact ? "md:grid-cols-1 xl:grid-cols-3" : "md:grid-cols-3"}`}>
        {offers.map((offer) => {
          const profile = getOfferProfile(offer.offer_id);
          return (
            <div key={offer.offer_id} className="rounded-xl border border-white/10 bg-black/10 p-4">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-sm font-semibold text-white">{offer.name}</p>
                  <p className="mt-1 text-xs uppercase tracking-[0.14em] text-gray-400">{profile.badge}</p>
                </div>
                <p className="text-sm font-semibold text-white">{offer.price_label}</p>
              </div>
              <p className="mt-3 text-sm text-gray-200">{profile.deliverable}</p>
              <p className="mt-2 text-xs leading-5 text-gray-400">Geeignet fuer: {profile.audience}</p>
              <p className="mt-2 text-xs leading-5 text-gray-500">Abgrenzung: {profile.boundary}</p>
              <button
                type="button"
                onClick={() => onCheckout(offer.offer_id)}
                disabled={!offer.checkout_enabled || isStartingCheckout}
                className="mt-4 w-full rounded-xl bg-brand-orange px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-brand-orangeHover disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isStartingCheckout ? "Checkout startet..." : offer.cta_label}
              </button>
            </div>
          );
        })}
      </div>
      <div className="mt-4 grid gap-3 lg:grid-cols-2">
        <div className="rounded-xl border border-white/10 bg-black/10 p-4">
          <p className="text-sm font-medium text-white">Professional, Express und Pro sind nicht dasselbe</p>
          <div className="mt-2 space-y-2 text-xs leading-5 text-gray-400">
            <p>Professional liefert strategischen Reportscope und erzeugt sichtbaren Service-Nachlauf.</p>
            <p>
              {expressOffer
                ? "Express ist nur ein Zeit- und Bearbeitungspfad und erweitert keine technische Analyse still im Hintergrund."
                : "Express bleibt ein separater Zeit- und Bearbeitungspfad und kein Ersatz fuer ein Analysepaket."}
            </p>
            <p>Pro ist der laufende Self-Serve-Pfad fuer wiederkehrende Teams, nicht der manuelle Professional-Servicepfad.</p>
          </div>
        </div>
        <div className="rounded-xl border border-white/10 bg-black/10 p-4">
          <p className="text-sm font-medium text-white">Was danach passiert</p>
          <div className="mt-2 space-y-2 text-xs leading-5 text-gray-400">
            <p>Erst erfolgreiche Runs verbrauchen Credits. Danach bleibt die Analyse in History und Projektkontext sichtbar.</p>
            <p>
              {pilotOffer
                ? "VNB Pilot bleibt ein separater Kontakt- und Pilotpfad fuer abgestimmte Netzbetreiber-Szenarien."
                : "VNB-nahe Pilotierung bleibt bewusst ausserhalb des Self-Serve-Upgrades."}
            </p>
          </div>
          <div className="mt-4 flex flex-col gap-2 sm:flex-row">
            <Link
              href="/settings"
              className="inline-flex items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
            >
              Tarifbereich oeffnen
            </Link>
            <Link
              href="/contact?intent=professional"
              className="inline-flex items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
            >
              Professional / Express anfragen
            </Link>
            <Link
              href="/contact?intent=vnb-pilot"
              className="inline-flex items-center justify-center rounded-xl border border-white/15 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-white/5"
            >
              VNB Pilot anfragen
            </Link>
          </div>
        </div>
      </div>
      <p className="mt-3 text-xs text-gray-400">
        Credits werden weiterhin erst bei erfolgreichem Abschluss verbucht. Finale Netzanschlussentscheidungen und
        Kapazitaetszusagen verbleiben beim zustaendigen Netzbetreiber.
      </p>
    </div>
  );
}
