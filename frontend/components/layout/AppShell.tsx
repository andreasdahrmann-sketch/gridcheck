"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import {
  Building2,
  FileText,
  FolderKanban,
  Map,
  Menu,
  Search,
  Settings,
  X,
} from "lucide-react";
import { Header } from "@/components/Header";
import { SiteFooter } from "@/components/layout/SiteFooter";
import UpgradeProBanner from "@/components/billing/UpgradeProBanner";
import { Button } from "@/components/ui/button";
import { me, type AuthUser } from "@/lib/api/auth";
import { canAccessVnbDashboard } from "@/lib/vnb-access";

const BASE_SIDEBAR_LINKS = [
  { href: "/projects", label: "Projekte", icon: FolderKanban },
  { href: "/projektierer", label: "Analyse", icon: Search },
  { href: "/map", label: "Karte", icon: Map },
  { href: "/reports", label: "Reports", icon: FileText },
  { href: "/settings", label: "Einstellungen", icon: Settings },
] as const;

const VNB_SIDEBAR_LINK = { href: "/vnb", label: "VNB", icon: Building2 } as const;

function isActivePath(pathname: string, href: string) {
  if (href === "/projects") return pathname.startsWith("/projects");
  if (href === "/projektierer") {
    return pathname.startsWith("/projektierer") || pathname.startsWith("/check");
  }
  if (href === "/vnb") return pathname.startsWith("/vnb");
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() ?? "";
  const [mobileOpen, setMobileOpen] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);

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

  const sidebarLinks = useMemo(() => {
    if (!user || !canAccessVnbDashboard(user)) {
      return [...BASE_SIDEBAR_LINKS];
    }
    return [
      BASE_SIDEBAR_LINKS[0],
      BASE_SIDEBAR_LINKS[1],
      VNB_SIDEBAR_LINK,
      ...BASE_SIDEBAR_LINKS.slice(2),
    ];
  }, [user]);

  const sidebar = (
    <nav className="flex flex-col gap-1 p-3" aria-label="App-Navigation">
      {sidebarLinks.map((item) => {
        const active = isActivePath(pathname, item.href);
        const Icon = item.icon;
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={() => setMobileOpen(false)}
            className={`flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
              active
                ? "border border-brand-cyan/25 bg-brand-cyan/10 text-brand-cyan"
                : "text-text-muted hover:bg-white/5 hover:text-white"
            }`}
          >
            <Icon className="h-4 w-4 shrink-0" aria-hidden />
            {item.label}
          </Link>
        );
      })}
    </nav>
  );

  return (
    <div className="flex min-h-screen flex-col bg-bg text-white">
      <Header />

      <div className="mx-auto flex w-full max-w-7xl flex-1 flex-col lg:flex-row">
        {/* Mobile toggle */}
        <div className="flex items-center justify-between border-b border-white/10 px-4 py-2 lg:hidden">
          <p className="text-xs font-medium uppercase tracking-[0.2em] text-text-dim">Arbeitsbereich</p>
          <Button
            type="button"
            variant="ghost"
            size="icon"
            className="h-9 w-9 rounded-lg border border-white/10 text-white"
            onClick={() => setMobileOpen((open) => !open)}
            aria-expanded={mobileOpen}
            aria-label={mobileOpen ? "Navigation schliessen" : "Navigation oeffnen"}
          >
            {mobileOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
          </Button>
        </div>

        {/* Sidebar: overlay on mobile, inline on lg+ */}
        {mobileOpen ? (
          <button
            type="button"
            className="fixed inset-0 z-40 bg-black/50 lg:hidden"
            aria-label="Navigation schliessen"
            onClick={() => setMobileOpen(false)}
          />
        ) : null}

        <aside
          className={`z-50 shrink-0 border-white/10 bg-bg-card/95 backdrop-blur lg:w-56 lg:border-r lg:bg-bg-card/60 ${
            mobileOpen
              ? "fixed inset-y-0 left-0 top-16 w-64 border-r shadow-xl lg:static lg:shadow-none"
              : "hidden lg:block"
          }`}
        >
          {sidebar}
        </aside>

        <main className="min-w-0 flex-1 px-4 py-4 sm:px-6 sm:py-6 lg:max-w-[calc(100%-14rem)]">
          <UpgradeProBanner />
          {children}
        </main>
      </div>

      <SiteFooter />
    </div>
  );
}
