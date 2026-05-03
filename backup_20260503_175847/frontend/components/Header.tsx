import Link from "next/link"
import { Logo } from "./Logo"

export function Header() {
  return (
    <header className="sticky top-0 z-40 backdrop-blur bg-bg/70 border-b border-border">
      <div className="max-w-6xl mx-auto px-6 h-16 flex items-center justify-between">
        <Link href="/"><Logo /></Link>
        <nav className="hidden md:flex items-center gap-6 text-sm text-text-muted">
          <Link href="/check" className="hover:text-white">GridCheck</Link>
          <Link href="#leistungen" className="hover:text-white">Leistungen</Link>
          <Link href="#kontakt" className="hover:text-white">Kontakt</Link>
        </nav>
        <Link href="/check"
          className="rounded-full bg-brand-orange hover:bg-brand-orangeHover text-white text-sm font-semibold px-4 py-2">
          GridCheck starten
        </Link>
      </div>
    </header>
  )
}
