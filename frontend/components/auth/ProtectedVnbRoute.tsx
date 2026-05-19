"use client";

import Link from "next/link";
import { useEffect, useState, type ReactNode } from "react";
import { ShieldAlert } from "lucide-react";
import { me, type AuthUser } from "@/lib/api/auth";
import { canAccessVnbDashboard, resolveVnbAccessState, vnbAccessMessage } from "@/lib/vnb-access";

type ProtectedVnbRouteProps = {
  children: ReactNode;
};

export function ProtectedVnbRoute({ children }: ProtectedVnbRouteProps) {
  const [user, setUser] = useState<AuthUser | null | undefined>(undefined);

  useEffect(() => {
    let active = true;
    me()
      .then((nextUser) => {
        if (active) setUser(nextUser);
      })
      .catch(() => {
        if (active) setUser(null);
      });
    return () => {
      active = false;
    };
  }, []);

  if (user === undefined) {
    return (
      <CenterShell>
        <p className="text-sm text-text-muted">VNB-Zugang wird geprueft...</p>
      </CenterShell>
    );
  }

  if (!user) {
    return (
      <CenterShell>
        <AccessPanel
          title="Anmeldung erforderlich"
          body="Bitte melden Sie sich an, um das Netzbetreiber-Dashboard zu nutzen."
          primaryHref="/login?next=%2Fvnb"
          primaryLabel="Anmelden"
        />
      </CenterShell>
    );
  }

  if (!canAccessVnbDashboard(user)) {
    const state = resolveVnbAccessState(user);
    const copy = vnbAccessMessage(state);
    return (
      <CenterShell>
        <AccessPanel
          title={copy.title}
          body={copy.body}
          primaryHref={state === "pending" ? "/contact?intent=vnb-pilot" : "/register?intent=vnb-pilot"}
          primaryLabel={state === "pending" ? "Freischaltung anfragen" : "Als Netzbetreiber registrieren"}
          secondaryHref="/settings"
          secondaryLabel="Einstellungen"
        />
      </CenterShell>
    );
  }

  return <>{children}</>;
}

function CenterShell({ children }: { children: ReactNode }) {
  return <div className="flex min-h-[50vh] items-center justify-center px-4 py-10">{children}</div>;
}

function AccessPanel({
  title,
  body,
  primaryHref,
  primaryLabel,
  secondaryHref,
  secondaryLabel,
}: {
  title: string;
  body: string;
  primaryHref: string;
  primaryLabel: string;
  secondaryHref?: string;
  secondaryLabel?: string;
}) {
  return (
    <div className="mx-auto max-w-lg rounded-[28px] border border-white/10 bg-white/5 p-6 text-center shadow-[0_20px_60px_rgba(0,0,0,0.24)]">
      <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-2xl border border-brand-orange/25 bg-brand-orange/10">
        <ShieldAlert className="h-6 w-6 text-brand-orange" aria-hidden />
      </div>
      <h2 className="mt-4 text-xl font-semibold text-white">{title}</h2>
      <p className="mt-3 text-sm leading-7 text-text-muted">{body}</p>
      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:justify-center">
        <Link
          href={primaryHref}
          className="inline-flex items-center justify-center rounded-2xl bg-brand-orange px-5 py-3 text-sm font-semibold text-white transition hover:bg-brand-orangeHover"
        >
          {primaryLabel}
        </Link>
        {secondaryHref && secondaryLabel ? (
          <Link
            href={secondaryHref}
            className="inline-flex items-center justify-center rounded-2xl border border-white/10 bg-white/5 px-5 py-3 text-sm font-semibold text-white transition hover:bg-white/10"
          >
            {secondaryLabel}
          </Link>
        ) : null}
      </div>
    </div>
  );
}
