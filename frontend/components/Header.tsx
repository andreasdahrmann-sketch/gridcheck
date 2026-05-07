import Link from "next/link"
import { Logo } from "./Logo"

export function Header() {
  return (
    <header className="sticky top-0 z-40 backdrop-blur bg-bg/75 border-b border-border">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/"><Logo /></Link>
        <nav className="hidden md:flex items-center gap-6 text-sm text-text-muted">
          <Link href="/check" className="hover:text-brand-cyan transition-colors">GridCheck</Link>
          <Link href="#leistungen" className="hover:text-brand-cyan transition-colors">Leistungen</Link>
          <Link href="#kontakt" className="hover:text-brand-cyan transition-colors">Kontakt</Link>
        </nav>
        <Link href="/check"
          className="rounded-full bg-brand-orange hover:bg-brand-orangeHover text-white text-sm font-semibold px-4 py-2 shadow-[0_0_0_1px_rgba(255,255,255,0.08)_inset] transition-colors">
          GridCheck starten
        </Link>
      </div>
    </header>
  )
}
