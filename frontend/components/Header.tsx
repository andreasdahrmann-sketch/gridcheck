"use client"
import Link from "next/link"
import { Logo } from "./Logo"
import { me, logout } from "@/lib/api/auth"
import { useEffect, useState } from "react"

export function Header() {
  const [loggedIn, setLoggedIn] = useState(false)

  useEffect(() => {
    me().then(() => setLoggedIn(true)).catch(() => setLoggedIn(false))
  }, [])

  return (
    <header className="sticky top-0 z-40 backdrop-blur bg-bg/75 border-b border-border">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/"><Logo /></Link>
        <nav className="hidden md:flex items-center gap-6 text-sm text-text-muted">
          <Link href="/projects" className="hover:text-brand-cyan transition-colors">Projekte</Link>
          <Link href="/settings" className="hover:text-brand-cyan transition-colors">Settings</Link>
          <Link href="/contact" className="hover:text-brand-cyan transition-colors">Kontakt</Link>
        </nav>
        {loggedIn ? (
          <button
            onClick={() => {
              logout().finally(() => {
                setLoggedIn(false)
                window.location.href = "/login"
              })
            }}
            className="rounded-full bg-brand-orange hover:bg-brand-orangeHover text-white text-sm font-semibold px-4 py-2 shadow-[0_0_0_1px_rgba(255,255,255,0.08)_inset] transition-colors"
          >
            Logout
          </button>
        ) : (
          <Link href="/login"
            className="rounded-full bg-brand-orange hover:bg-brand-orangeHover text-white text-sm font-semibold px-4 py-2 shadow-[0_0_0_1px_rgba(255,255,255,0.08)_inset] transition-colors">
            Login
          </Link>
        )}
      </div>
    </header>
  )
}
