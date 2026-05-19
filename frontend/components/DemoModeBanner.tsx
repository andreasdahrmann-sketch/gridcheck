"use client";

interface DemoModeBannerProps {
  title: string;
  description?: string;
  className?: string;
}

export default function DemoModeBanner({ title, description, className = "" }: DemoModeBannerProps) {
  return (
    <div
      role="status"
      className={`rounded-2xl border border-yellow-500/40 bg-yellow-500/15 px-4 py-3 md:px-5 md:py-4 ${className}`}
    >
      <p className="text-sm font-bold tracking-wide text-yellow-300">[DEMO] {title}</p>
      {description ? (
        <p className="mt-1 text-sm leading-6 text-yellow-100/90">{description}</p>
      ) : (
        <p className="mt-1 text-sm leading-6 text-yellow-100/90">
          Vordefinierte Beispieldaten ohne echte Netzbetreiber-Freigabe. Ergebnis dient der Produktdemonstration, nicht
          der verbindlichen Netzanschlussprüfung.
        </p>
      )}
    </div>
  );
}
