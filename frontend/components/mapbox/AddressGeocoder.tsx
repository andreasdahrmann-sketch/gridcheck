"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Loader2, MapPin, Search } from "lucide-react";
import { hasMapboxToken } from "@/lib/mapbox/config";
import { MapboxGeocodingError } from "@/lib/mapbox/geocoding";
import { searchMapboxPlaces } from "@/lib/mapbox/search-places";

export type AddressGeocodeSelection = {
  address_hint: string;
  latitude: number;
  longitude: number;
  plz?: string;
  ort?: string;
  label: string;
};

type Props = {
  value: string;
  plz?: string;
  ort?: string;
  onChange: (addressHint: string) => void;
  onSelect: (selection: AddressGeocodeSelection) => void;
  placeholder?: string;
  disabled?: boolean;
};

export default function AddressGeocoder({
  value,
  plz,
  ort,
  onChange,
  onSelect,
  placeholder = "Adresse, Ort oder Gewerbegebiet suchen…",
  disabled = false,
}: Props) {
  const listId = useId();
  const [suggestions, setSuggestions] = useState<
    Array<{ label: string; lat: number; lng: number; plz?: string; ort?: string }>
  >([]);
  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  const mapboxReady = hasMapboxToken();

  const runSearch = useCallback(
    async (query: string) => {
      if (!mapboxReady || query.trim().length < 3) {
        setSuggestions([]);
        setError(mapboxReady ? null : "Mapbox-Token fehlt – Adresssuche nicht verfuegbar.");
        return;
      }

      setIsSearching(true);
      setError(null);
      try {
        const results = await searchMapboxPlaces(query, { plz, ort, limit: 6 });
        setSuggestions(
          results.map((item) => ({
            label: item.label,
            lat: item.lat,
            lng: item.lng,
            plz: item.plz,
            ort: item.ort,
          })),
        );
        setOpen(results.length > 0);
      } catch (err) {
        setSuggestions([]);
        setError(
          err instanceof MapboxGeocodingError
            ? err.message
            : err instanceof Error
              ? err.message
              : "Adresssuche fehlgeschlagen.",
        );
      } finally {
        setIsSearching(false);
      }
    },
    [mapboxReady, ort, plz],
  );

  useEffect(() => {
    if (!open) return;
    const handleClick = (event: MouseEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, [open]);

  useEffect(() => {
    if (!value.trim() || value.trim().length < 3) {
      setSuggestions([]);
      return;
    }

    const timer = window.setTimeout(() => {
      void runSearch(value);
    }, 320);

    return () => window.clearTimeout(timer);
  }, [value, runSearch]);

  function pickSuggestion(item: (typeof suggestions)[number]) {
    onSelect({
      address_hint: item.label,
      latitude: item.lat,
      longitude: item.lng,
      plz: item.plz,
      ort: item.ort,
      label: item.label,
    });
    onChange(item.label);
    setOpen(false);
    setSuggestions([]);
  }

  return (
    <div ref={containerRef} className="relative">
      <label className="mb-1 block text-xs uppercase tracking-[0.16em] text-text-dim">
        Adresse oder Standort suchen
      </label>
      <div className="relative">
        <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-text-dim" aria-hidden />
        <input
          type="search"
          role="combobox"
          aria-expanded={open}
          aria-controls={listId}
          aria-autocomplete="list"
          disabled={disabled || !mapboxReady}
          className="w-full rounded-xl border border-border/70 bg-white/5 py-2.5 pl-9 pr-10 text-sm text-white placeholder:text-text-dim focus:border-brand-cyan/60 focus:outline-none focus:ring-1 focus:ring-brand-cyan/25 disabled:cursor-not-allowed disabled:opacity-60"
          value={value}
          onChange={(e) => {
            onChange(e.target.value);
            setOpen(true);
          }}
          onFocus={() => {
            if (suggestions.length > 0) setOpen(true);
          }}
          placeholder={mapboxReady ? placeholder : "Mapbox-Token fehlt (NEXT_PUBLIC_MAPBOX_TOKEN)"}
        />
        {isSearching ? (
          <Loader2 className="absolute right-3 top-3 h-4 w-4 animate-spin text-brand-cyan" aria-hidden />
        ) : (
          <MapPin className="absolute right-3 top-3 h-4 w-4 text-text-dim" aria-hidden />
        )}
      </div>

      {error ? <p className="mt-2 text-xs text-amber-200">{error}</p> : null}

      {open && suggestions.length > 0 ? (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-30 mt-1 max-h-56 w-full overflow-auto rounded-xl border border-white/10 bg-bg-card py-1 shadow-xl"
        >
          {suggestions.map((item) => (
            <li key={`${item.lng}-${item.lat}-${item.label}`} role="option">
              <button
                type="button"
                className="w-full px-3 py-2.5 text-left text-sm text-white transition hover:bg-white/5"
                onClick={() => pickSuggestion(item)}
              >
                {item.label}
              </button>
            </li>
          ))}
        </ul>
      ) : null}

      <p className="mt-2 text-xs leading-5 text-text-muted">
        Vorschlag aus Mapbox-Geocoding. Exakte Koordinaten koennen Sie optional unter „Erweitert“ setzen.
      </p>
    </div>
  );
}
