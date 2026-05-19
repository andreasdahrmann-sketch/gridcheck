"use client"

import Link from "next/link"
import { Menu, LogOut } from "lucide-react"
import { usePathname, useRouter } from "next/navigation"
import { useEffect, useMemo, useState } from "react"
import { Logo } from "./Logo"
import { me, logout, type AuthUser } from "@/lib/api/auth"
import { canAccessVnbDashboard } from "@/lib/vnb-access"
import { Button } from "@/components/ui/button"
import { PwaInstallPrompt } from "@/components/mobile/PwaInstallPrompt"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet"

const baseNavLinks = [
  { href: "/", label: "Start" },
  { href: "/projektierer", label: "Projektierer" },
  { href: "/preise", label: "Tarife" },
  { href: "/projects", label: "Projekte" },
  { href: "/site-markers", label: "Vor-Ort-Marker" },
  { href: "/settings", label: "Einstellungen" },
  { href: "/contact", label: "Kontakt" },
]

export function Header() {
  const pathname = usePathname()
  const router = useRouter()
  const [user, setUser] = useState<AuthUser | null>(null)
  const [mobileOpen, setMobileOpen] = useState(false)
  const [isLoggingOut, setIsLoggingOut] = useState(false)

  useEffect(() => {
    let active = true

    me()
      .then((nextUser) => {
        if (active) {
          setUser(nextUser)
        }
      })
      .catch(() => {
        if (active) {
          setUser(null)
        }
      })

    return () => {
      active = false
    }
  }, [])

  const activePath = useMemo(() => {
    if (!pathname) return "/"
    if (pathname.startsWith("/projektierer") || pathname.startsWith("/check")) return "/projektierer"
    if (pathname.startsWith("/projects")) return "/projects"
    if (pathname.startsWith("/site-markers")) return "/site-markers"
    if (pathname.startsWith("/ops")) return "/ops"
    if (pathname.startsWith("/preise")) return "/preise"
    if (pathname.startsWith("/settings")) return "/settings"
    if (pathname.startsWith("/contact")) return "/contact"
    if (pathname.startsWith("/vnb")) return "/vnb"
    return "/"
  }, [pathname])

  const navLinks = useMemo(() => {
    const vnbLink = user && canAccessVnbDashboard(user) ? [{ href: "/vnb", label: "VNB" }] : []
    const core = [
      baseNavLinks[0],
      baseNavLinks[1],
      ...vnbLink,
      baseNavLinks[2],
      baseNavLinks[3],
      baseNavLinks[4],
    ]
    if (user?.role === "admin") {
      return [...core, { href: "/ops", label: "OPS" }, baseNavLinks[5], baseNavLinks[6]]
    }
    return [...core, baseNavLinks[5], baseNavLinks[6]]
  }, [user])

  async function handleLogout() {
    if (isLoggingOut) return

    setIsLoggingOut(true)
    try {
      await logout()
    } finally {
      setUser(null)
      setMobileOpen(false)
      router.replace("/login")
    }
  }

  return (
    <header className="safe-area-top sticky top-0 z-40 border-b border-border bg-bg/80 backdrop-blur">
      <div className="mx-auto flex min-h-16 max-w-6xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
        <Link href="/" className="shrink-0">
          <Logo />
        </Link>

        <nav className="hidden items-center gap-2 md:flex">
          {navLinks.map((item) => {
            const isActive = item.href === activePath
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
                  isActive
                    ? "bg-white/10 text-white"
                    : "text-text-muted hover:bg-white/5 hover:text-white"
                }`}
              >
                {item.label}
              </Link>
            )
          })}
        </nav>

        <div className="flex items-center gap-2">
          <PwaInstallPrompt compact className="h-10 w-10 rounded-xl bg-brand-cyan text-slate-950 hover:bg-brand-cyan/90 md:hidden" />
          <PwaInstallPrompt className="hidden h-10 rounded-full border border-brand-cyan/20 bg-brand-cyan/10 px-4 text-brand-cyan hover:bg-brand-cyan/15 md:inline-flex" />
          {user ? (
            <Button
              type="button"
              onClick={handleLogout}
              disabled={isLoggingOut}
              className="hidden h-10 rounded-full bg-brand-orange px-4 text-white hover:bg-brand-orangeHover md:inline-flex"
            >
              {isLoggingOut ? "Logout..." : "Logout"}
            </Button>
          ) : (
            <Link
              href="/login"
              className="hidden rounded-full bg-brand-orange px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-brand-orangeHover md:inline-flex"
            >
              Login
            </Link>
          )}

          <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
            <SheetTrigger asChild>
              <Button
                type="button"
                variant="ghost"
                size="icon"
                className="h-10 w-10 rounded-xl border border-white/10 bg-white/5 text-white hover:bg-white/10 md:hidden"
              >
                <Menu className="h-5 w-5" />
                <span className="sr-only">Navigation oeffnen</span>
              </Button>
            </SheetTrigger>
            <SheetContent
              side="right"
              className="w-[88vw] max-w-sm border-l border-border bg-bg px-0 text-white"
            >
              <SheetHeader className="border-b border-white/10 px-5 pb-4 pt-5">
                <SheetTitle className="text-white">Navigation</SheetTitle>
                <SheetDescription className="text-text-muted">
                  Direkter Zugriff auf Schnellcheck, Projekte, Vor-Ort-Marker, Einstellungen und Kontakt.
                </SheetDescription>
              </SheetHeader>

              <div className="px-5 py-5">
                {user ? (
                  <div className="rounded-2xl border border-white/10 bg-white/5 px-4 py-4">
                    <p className="text-xs uppercase tracking-[0.2em] text-text-dim">Eingeloggt als</p>
                    <p className="mt-2 text-sm font-medium text-white">{user.full_name || user.email}</p>
                    <p className="mt-1 text-sm text-text-muted">{user.role}</p>
                  </div>
                ) : null}

                <nav className="mt-5 space-y-2">
                  {navLinks.map((item) => {
                    const isActive = item.href === activePath
                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        onClick={() => setMobileOpen(false)}
                        className={`flex items-center justify-between rounded-2xl border px-4 py-3 text-sm font-medium transition-colors ${
                          isActive
                            ? "border-brand-cyan/25 bg-brand-cyan/10 text-white"
                            : "border-white/10 bg-white/5 text-text-muted hover:text-white"
                        }`}
                      >
                        <span>{item.label}</span>
                        {isActive ? <span className="text-xs text-brand-cyan">Aktiv</span> : null}
                      </Link>
                    )
                  })}
                </nav>

                <div className="mt-6">
                  {user ? (
                    <Button
                      type="button"
                      onClick={handleLogout}
                      disabled={isLoggingOut}
                      className="h-11 w-full rounded-2xl bg-brand-orange text-white hover:bg-brand-orangeHover"
                    >
                      <LogOut className="mr-2 h-4 w-4" />
                      {isLoggingOut ? "Logout..." : "Logout"}
                    </Button>
                  ) : (
                    <Link
                      href="/login"
                      onClick={() => setMobileOpen(false)}
                      className="inline-flex h-11 w-full items-center justify-center rounded-2xl bg-brand-orange px-4 text-sm font-semibold text-white transition-colors hover:bg-brand-orangeHover"
                    >
                      Login
                    </Link>
                  )}
                </div>
              </div>
            </SheetContent>
          </Sheet>
        </div>
      </div>
    </header>
  )
}
