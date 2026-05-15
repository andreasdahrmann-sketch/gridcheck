import Link from "next/link";

const legalLinks = [
  { href: "/impressum", label: "Impressum" },
  { href: "/datenschutz", label: "Datenschutz" },
  { href: "/agb", label: "AGB" },
  { href: "/contact", label: "Kontakt" },
] as const;

export function SiteFooter() {
  return (
    <footer className="safe-area-bottom mt-auto border-t border-white/10 bg-bg/90">
      <div className="mx-auto flex max-w-6xl flex-col gap-4 px-4 py-6 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <p className="text-xs leading-5 text-text-dim">
          GridCheck liefert vorlaeufige Netzanschluss-Diagnostik – keine verbindliche Netzanschlusszusage.
        </p>
        <nav className="flex flex-wrap gap-x-4 gap-y-2 text-sm" aria-label="Rechtliches und Kontakt">
          {legalLinks.map((item) => (
            <Link
              key={item.href}
              href={item.href}
              className="text-text-muted transition-colors hover:text-brand-cyan"
            >
              {item.label}
            </Link>
          ))}
        </nav>
      </div>
    </footer>
  );
}
