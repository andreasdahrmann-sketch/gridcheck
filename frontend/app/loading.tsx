export default function RootLoading() {
  return (
    <main
      role="status"
      aria-live="polite"
      aria-busy="true"
      className="flex min-h-[60vh] flex-1 items-center justify-center px-6 py-16"
    >
      <div className="w-full max-w-md space-y-6">
        <div className="flex items-center gap-3">
          <span
            aria-hidden="true"
            className="inline-block h-3 w-3 animate-pulse rounded-full bg-brand-orange"
          />
          <span className="text-sm font-medium uppercase tracking-wider text-text-muted">
            GridCheck lädt …
          </span>
        </div>

        <div className="card space-y-4">
          <div className="h-5 w-2/3 animate-pulse rounded-md bg-bg-elev" />
          <div className="space-y-2">
            <div className="h-3 w-full animate-pulse rounded-md bg-bg-elev" />
            <div className="h-3 w-5/6 animate-pulse rounded-md bg-bg-elev" />
            <div className="h-3 w-3/4 animate-pulse rounded-md bg-bg-elev" />
          </div>
          <div className="flex gap-3 pt-2">
            <div className="h-9 w-28 animate-pulse rounded-full bg-bg-elev" />
            <div className="h-9 w-24 animate-pulse rounded-full bg-bg-elev" />
          </div>
        </div>

        <p className="text-center text-xs text-text-dim">
          Wenn das Laden ungewöhnlich lange dauert, bitte Seite neu laden.
        </p>
      </div>
      <span className="sr-only">Inhalt wird geladen</span>
    </main>
  );
}
