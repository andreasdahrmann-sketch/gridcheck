"use client";

import Link from "next/link";
import { useQuery } from "@tanstack/react-query";
import { Sparkles } from "lucide-react";
import { getBillingStatus } from "@/lib/api/billing";
import { isPaidBillingStatus } from "@/lib/billing-paid";

export default function UpgradeProBanner() {
  const billingQuery = useQuery({
    queryKey: ["billing-status"],
    queryFn: getBillingStatus,
    staleTime: 60_000,
    retry: false,
  });

  const billing = billingQuery.data;

  if (billingQuery.isLoading || billingQuery.isError || !billing) {
    return null;
  }

  if (isPaidBillingStatus(billing)) {
    return null;
  }

  return (
    <div className="mb-6 rounded-2xl border border-brand-orange/25 bg-brand-orange/10 px-4 py-3 sm:flex sm:items-center sm:justify-between sm:gap-4">
      <div className="flex min-w-0 items-start gap-3">
        <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-brand-orange" aria-hidden />
        <div>
          <p className="text-sm font-semibold text-white">Upgrade Pro</p>
          <p className="mt-1 text-xs leading-5 text-text-muted">
            {billing.free_checks_remaining <= 0
              ? "Ihre Free Checks sind verbraucht. Pro oder Pay-per-Use-Pakete schalten weitere Analysen frei."
              : `Noch ${billing.free_checks_remaining} Free Check(s) – Pro fuer laufende Pipeline ohne Kontingentgrenze.`}
          </p>
        </div>
      </div>
      <Link
        href="/settings"
        className="mt-3 inline-flex shrink-0 items-center justify-center rounded-xl bg-brand-orange px-4 py-2 text-sm font-semibold text-white transition hover:bg-brand-orangeHover sm:mt-0"
      >
        Tarife ansehen
      </Link>
    </div>
  );
}
