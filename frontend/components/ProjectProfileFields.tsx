"use client";

import { useState } from "react";
import AddressGeocoder, { type AddressGeocodeSelection } from "@/components/mapbox/AddressGeocoder";
import type {
  EnvironmentalRouteInput,
  GridCheckInput,
  N1FeederInput,
  N1TransformerInput,
  NetzanschlusspunktInput,
  N1DataSource,
  ProjectLocationInput,
  ProjectComponentInput,
  StakeholderContextInput,
  StorageProfileInput,
  Topologie,
  UmspannwerkInput,
} from "@/types";

type ProjectProfileValue = Partial<GridCheckInput> & {
  kundentyp?: string;
  projektname?: string;
  erzeugungstyp?: string;
};

type Props = {
  value: ProjectProfileValue;
  onChange: (next: ProjectProfileValue) => void;
  compact?: boolean;
};

const sectionClass =
  "rounded-[24px] border border-border/70 bg-bg-card/80 p-4 shadow-[0_12px_34px_rgba(0,0,0,0.16)]";
const titleClass = "mb-3 text-base font-semibold text-white";
const labelClass = "mb-1 block text-xs uppercase tracking-[0.16em] text-text-dim";
const inputClass =
  "w-full rounded-xl border border-border/70 bg-white/5 px-3 py-2.5 text-sm text-white placeholder:text-text-dim focus:border-brand-cyan/60 focus:outline-none focus:ring-1 focus:ring-brand-cyan/25";
const selectFieldClass = `${inputClass} form-select cursor-pointer`;
const helperTextClass = "mt-2 text-xs leading-5 text-text-muted";
const addButtonClass =
  "inline-flex min-h-10 items-center justify-center rounded-xl border border-brand-cyan/25 bg-brand-cyan/10 px-3 py-2 text-sm font-medium text-brand-cyan transition hover:bg-brand-cyan/15";
const removeButtonClass =
  "inline-flex min-h-9 items-center justify-center rounded-xl border border-rose-400/20 bg-rose-500/10 px-3 py-2 text-xs font-medium text-rose-200 transition hover:bg-rose-500/15";
const checkboxClass = "h-4 w-4 rounded border-border/70 bg-black/10 text-brand-cyan focus:ring-brand-cyan/30";

const EMPTY_COMPONENT: ProjectComponentInput = {
  component_type: "pv",
  capacity_kw: 1000,
  controllable: false,
};

const EMPTY_TRAFO: N1TransformerInput = {
  label: "",
  sn_mva: 40,
  belastung_aktuell_mw: 10,
};

const EMPTY_ABGANG: N1FeederInput = {
  label: "",
  i_max_a: 630,
  belastung_aktuell_a: 300,
  reserve_n1_a: undefined,
  primary: false,
  verfuegbar_im_n1: true,
  koppelbar: true,
  datenquelle: "planner_assumption",
};

const TOPOLOGIE_OPTIONS: Array<{ value: Topologie; label: string; detail: string }> = [
  { value: "radial", label: "Radial (Legacy)", detail: "Wird im Backend konservativ wie Stich behandelt." },
  { value: "ring", label: "Ring (Legacy)", detail: "Wird im Backend als offener Ring interpretiert." },
  { value: "stich", label: "Stich", detail: "Keine belastbare N-1-Reserve." },
  {
    value: "stich_mit_notverbindung",
    label: "Stich mit Notverbindung",
    detail: "Umschaltbarer Reservepfad, aber nicht unterbrechungsfrei.",
  },
  { value: "ring_offen", label: "Ring offen", detail: "Typischer MS-Screening-Fall mit Reservepfad." },
  {
    value: "ring_geschlossen",
    label: "Ring geschlossen",
    detail: "Reservepfad vorhanden, Betriebsfuehrung gesondert abstimmen.",
  },
  { value: "doppelstich", label: "Doppelstich", detail: "Zweiter Einspeisepfad separat gefuehrt." },
  { value: "vermascht", label: "Vermascht", detail: "Mehrere Pfade, Screening bleibt konservativ." },
  { value: "unbekannt", label: "Unbekannt", detail: "Nur geringe Nachweistiefe moeglich." },
];

const DATA_SOURCE_OPTIONS: Array<{ value: N1DataSource; label: string }> = [
  { value: "unknown", label: "Unbekannt / offen" },
  { value: "planner_assumption", label: "Planerannahme" },
  { value: "user_estimate", label: "Nutzerschaetzung" },
  { value: "dso_verified", label: "VNB-verifiziert" },
];

function componentLabel(type: ProjectComponentInput["component_type"]): string {
  switch (type) {
    case "pv":
      return "PV";
    case "wind":
      return "Wind";
    case "battery":
      return "Batteriespeicher";
    case "charging":
      return "Ladeinfrastruktur";
    case "heat_pump":
      return "Waermepumpe";
    case "electrolyzer":
      return "Elektrolyseur";
    case "substation":
      return "Umspannwerk / Schaltanlage";
    case "load":
      return "Verbraucher / Last";
    default:
      return "Sonstige Komponente";
  }
}

export default function ProjectProfileFields({ value, onChange, compact = false }: Props) {
  const projectComponents = value.project_components ?? [];
  const stakeholderContext: StakeholderContextInput = value.stakeholder_context ?? {};
  const storageProfile: StorageProfileInput = value.storage_profile ?? {};
  const netzanschlusspunkt: NetzanschlusspunktInput = value.netzanschlusspunkt ?? {};
  const environmentalRoute: EnvironmentalRouteInput = value.environmental_route ?? {};
  const projectLocation: ProjectLocationInput = value.project_location ?? {};
  const umspannwerk: UmspannwerkInput = value.umspannwerk ?? {};
  const activeCustomerType = value.kundentyp ?? stakeholderContext.customer_type ?? "";
  const [showAdvancedCoords, setShowAdvancedCoords] = useState(
    Boolean(projectLocation.latitude != null || projectLocation.longitude != null),
  );

  const patch = (delta: Partial<ProjectProfileValue>) => onChange({ ...value, ...delta });
  const patchStakeholder = (delta: Partial<StakeholderContextInput>) =>
    patch({ stakeholder_context: { ...stakeholderContext, ...delta } });
  const patchStorage = (delta: Partial<StorageProfileInput>) =>
    patch({ storage_profile: { ...storageProfile, ...delta } });
  const patchNap = (delta: Partial<NetzanschlusspunktInput>) =>
    patch({ netzanschlusspunkt: { ...netzanschlusspunkt, ...delta } });
  const patchEnvironment = (delta: Partial<EnvironmentalRouteInput>) =>
    patch({ environmental_route: { ...environmentalRoute, ...delta } });
  const patchLocation = (delta: Partial<ProjectLocationInput>) =>
    patch({ project_location: { ...projectLocation, ...delta } });
  const patchUmspannwerk = (delta: Partial<UmspannwerkInput>) =>
    patch({ umspannwerk: { ...umspannwerk, ...delta } });

  const updateComponent = (index: number, delta: Partial<ProjectComponentInput>) => {
    const next = [...projectComponents];
    next[index] = { ...next[index], ...delta };
    patch({ project_components: next });
  };

  const updateTrafo = (index: number, delta: Partial<N1TransformerInput>) => {
    const next = [...(umspannwerk.trafos ?? [])];
    next[index] = { ...next[index], ...delta };
    patchUmspannwerk({ trafos: next });
  };

  const updateAbgang = (index: number, delta: Partial<N1FeederInput>) => {
    const next = [...(umspannwerk.abgaenge ?? [])];
    next[index] = { ...next[index], ...delta };
    patchUmspannwerk({ abgaenge: next });
  };

  const addComponent = () => patch({ project_components: [...projectComponents, { ...EMPTY_COMPONENT }] });
  const removeComponent = (index: number) =>
    patch({ project_components: projectComponents.filter((_, currentIndex) => currentIndex !== index) });
  const addTrafo = () => patchUmspannwerk({ trafos: [...(umspannwerk.trafos ?? []), { ...EMPTY_TRAFO }] });
  const removeTrafo = (index: number) =>
    patchUmspannwerk({ trafos: (umspannwerk.trafos ?? []).filter((_, currentIndex) => currentIndex !== index) });
  const addAbgang = () => patchUmspannwerk({ abgaenge: [...(umspannwerk.abgaenge ?? []), { ...EMPTY_ABGANG }] });
  const removeAbgang = (index: number) =>
    patchUmspannwerk({ abgaenge: (umspannwerk.abgaenge ?? []).filter((_, currentIndex) => currentIndex !== index) });

  return (
    <div className="space-y-4">
      <div className={sectionClass}>
        <h3 className={titleClass}>Stakeholder & Projektkontext</h3>
        <div className={`grid ${compact ? "md:grid-cols-2" : "md:grid-cols-3"} gap-3`}>
          <div>
            <label className={labelClass}>Kundentyp</label>
            <select
              className={selectFieldClass}
              value={value.kundentyp ?? stakeholderContext.customer_type ?? ""}
              onChange={(e) => {
                patch({ kundentyp: e.target.value });
                patchStakeholder({
                  customer_type: e.target.value
                    ? (e.target.value as StakeholderContextInput["customer_type"])
                    : undefined,
                });
              }}
            >
              <option value="">-- Waehlen --</option>
              <option value="projektierer">Projektierer</option>
              <option value="speicherbetreiber">Speicherbetreiber</option>
              <option value="netzbetreiber">Netzbetreiber</option>
              <option value="investor">Investor</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Prioritaetsfokus</label>
            <select
              className={selectFieldClass}
              value={stakeholderContext.priority_focus ?? "balanced"}
              onChange={(e) =>
                patchStakeholder({
                  priority_focus: e.target.value as StakeholderContextInput["priority_focus"],
                })
              }
            >
              <option value="balanced">Ausgewogen</option>
              <option value="kosten">Kosten</option>
              <option value="zeit">Zeit</option>
              <option value="netz">Netzrobustheit</option>
              <option value="genehmigung">Genehmigung / Trasse</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Projektreife</label>
            <select
              className={selectFieldClass}
              value={value.projektreife ?? ""}
              onChange={(e) =>
                patch({
                  projektreife: e.target.value
                    ? (e.target.value as GridCheckInput["projektreife"])
                    : undefined,
                })
              }
            >
              <option value="">-- Offen --</option>
              <option value="idee">Idee</option>
              <option value="planung">Planung</option>
              <option value="genehmigt">Genehmigt</option>
              <option value="baubereit">Baubereit</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Foerderfrist</label>
            <input
              type="date"
              className={inputClass}
              value={value.foerderfrist ?? ""}
              onChange={(e) => patch({ foerderfrist: e.target.value || undefined })}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(value.baugenehmigung_vorhanden)}
              onChange={(e) => patch({ baugenehmigung_vorhanden: e.target.checked })}
            />
            Baugenehmigung vorhanden
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(stakeholderContext.netzbetreiber_dialog_needed)}
              onChange={(e) => patchStakeholder({ netzbetreiber_dialog_needed: e.target.checked })}
            />
            Fruher VNB-Dialog erforderlich
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(stakeholderContext.investor_relevant || activeCustomerType === "investor")}
              onChange={(e) => patchStakeholder({ investor_relevant: e.target.checked })}
            />
            Due-Diligence / Investsicht relevant
          </label>
        </div>
        <p className={helperTextClass}>
          {activeCustomerType === "netzbetreiber"
            ? "Im VNB-Pfad bleiben Netz- und Umspannwerksdaten konservativ. Ohne konkrete Nachweise entsteht keine Scheinsicherheit."
            : activeCustomerType === "investor"
              ? "Im Invest-Pfad werden Standort-, Risiko- und Kostenbandbreiten verdichtet; rohe interne Netzdaten bleiben bewusst ausser Sicht."
              : "Stakeholder-Kontext steuert Reportsprache, Fokus und Sichtbarkeit, ohne die technische Engine-Logik ins Frontend zu verlagern."}
        </p>
      </div>

      <div className={sectionClass}>
        <h3 className={titleClass}>Standortpraezisierung</h3>
        <div className={`grid ${compact ? "md:grid-cols-2" : "md:grid-cols-3"} gap-3`}>
          <div className={compact ? "md:col-span-2" : "md:col-span-3"}>
            <AddressGeocoder
              value={projectLocation.address_hint ?? ""}
              plz={value.plz}
              ort={value.ort}
              onChange={(hint) => patchLocation({ address_hint: hint || undefined })}
              onSelect={(selection: AddressGeocodeSelection) => {
                patchLocation({
                  address_hint: selection.address_hint,
                  latitude: selection.latitude,
                  longitude: selection.longitude,
                });
                if (selection.plz && !value.plz) patch({ plz: selection.plz });
                if (selection.ort && !value.ort) patch({ ort: selection.ort });
              }}
            />
          </div>
          {showAdvancedCoords ? (
            <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label className={labelClass}>Breitengrad</label>
            <input
              type="number"
              step="0.000001"
              className={inputClass}
              value={projectLocation.latitude ?? ""}
              onChange={(e) =>
                patchLocation({ latitude: e.target.value ? Number(e.target.value) : undefined })
              }
              placeholder="z.B. 52.379189"
            />
          </div>
          <div>
            <label className={labelClass}>Laengengrad</label>
            <input
              type="number"
              step="0.000001"
              className={inputClass}
              value={projectLocation.longitude ?? ""}
              onChange={(e) =>
                patchLocation({ longitude: e.target.value ? Number(e.target.value) : undefined })
              }
              placeholder="z.B. 9.761990"
            />
          </div>
            </div>
          ) : null}
          <div>
            <label className={labelClass}>Flaechenrahmen (Radius m, optional)</label>
            <input
              type="number"
              step="10"
              className={inputClass}
              value={projectLocation.area_radius_m ?? ""}
              onChange={(e) =>
                patchLocation({ area_radius_m: e.target.value ? Number(e.target.value) : undefined })
              }
              placeholder="z.B. 250"
            />
          </div>
          <button
            type="button"
            className="text-xs font-medium text-brand-cyan underline-offset-2 hover:underline"
            onClick={() => setShowAdvancedCoords((open) => !open)}
          >
            {showAdvancedCoords ? "Erweitert: Koordinaten ausblenden" : "Erweitert: Breiten-/Laengengrad manuell"}
          </button>
        </div>
        <p className={helperTextClass}>
          Prioritaet fuer die Kartenlage: Adresssuche bzw. exakte Koordinate, dann Ort/PLZ. Ohne belastbare Quelle wird
          die Lage bewusst als ungefaehr markiert.
        </p>
      </div>

      <div className={sectionClass}>
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h3 className={titleClass}>Netzgrundlage & N-1-Kontext</h3>
            <p className="max-w-3xl text-sm leading-6 text-text-muted">
              Diese Angaben erhoehen nicht kuenstlich die Sicherheit, sondern machen die Nachweistiefe
              fuer das N-1-Screening transparent: Topologie, Reservepfade, Umspannwerk und Datengrundlage.
            </p>
          </div>
          <div className="rounded-2xl border border-brand-orange/20 bg-brand-orange/10 px-3 py-3 text-xs leading-5 text-text-muted sm:max-w-xs">
            Ohne verifizierte VNB-Daten bleibt die N-1-Aussage bewusst konservativ und erreicht im MVP
            maximal N1-3.
          </div>
        </div>

        <div className={`mt-4 grid ${compact ? "md:grid-cols-2" : "md:grid-cols-4"} gap-3`}>
          <div>
            <label className={labelClass}>Topologie</label>
            <select
              className={selectFieldClass}
              value={value.topologie ?? "unbekannt"}
              onChange={(e) => patch({ topologie: e.target.value as GridCheckInput["topologie"] })}
            >
              {TOPOLOGIE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
            <p className={helperTextClass}>
              {TOPOLOGIE_OPTIONS.find((option) => option.value === (value.topologie ?? "unbekannt"))?.detail}
            </p>
          </div>

          <div>
            <label className={labelClass}>Datengrundlage N-1</label>
            <select
              className={selectFieldClass}
              value={value.n1_datengrundlage ?? "unknown"}
              onChange={(e) => patch({ n1_datengrundlage: e.target.value as N1DataSource })}
            >
              {DATA_SOURCE_OPTIONS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className={labelClass}>Restkapazitaet MS (MVA)</label>
            <input
              type="number"
              step="0.1"
              className={inputClass}
              value={value.restkapazitaet_ms_mva ?? ""}
              onChange={(e) =>
                patch({ restkapazitaet_ms_mva: e.target.value ? Number(e.target.value) : undefined })
              }
              placeholder="z.B. 10"
            />
          </div>

          <div>
            <label className={labelClass}>Umschaltzeit (min)</label>
            <input
              type="number"
              step="1"
              className={inputClass}
              value={value.umschaltzeit_min ?? ""}
              onChange={(e) =>
                patch({ umschaltzeit_min: e.target.value ? Number(e.target.value) : undefined })
              }
              placeholder="z.B. 15"
            />
          </div>
        </div>

        <div className="mt-5 grid gap-4 xl:grid-cols-2">
          <div className="rounded-[22px] border border-white/10 bg-black/10 p-4">
            <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h4 className="text-sm font-semibold text-white">Umspannwerk / Traforeserve</h4>
                <p className="mt-1 text-xs leading-5 text-text-muted">
                  Pro Trafo nur bekannte oder planerisch belastbare Werte erfassen.
                </p>
              </div>
              <button type="button" onClick={addTrafo} className={addButtonClass}>
                Trafo hinzufuegen
              </button>
            </div>

            {(umspannwerk.trafos ?? []).length === 0 ? (
              <p className="rounded-2xl border border-dashed border-white/10 bg-white/5 px-3 py-3 text-sm text-text-muted">
                Noch keine Trafodaten erfasst. Ohne diese bleibt der Trafo-N-1-Nachweis offen.
              </p>
            ) : null}

            <div className="space-y-3">
              {(umspannwerk.trafos ?? []).map((trafo, index) => (
                <div key={`trafo-${index}`} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="text-sm font-medium text-white">Trafo {index + 1}</div>
                    <button type="button" onClick={() => removeTrafo(index)} className={removeButtonClass}>
                      Entfernen
                    </button>
                  </div>

                  <div className={`mt-3 grid ${compact ? "md:grid-cols-2" : "md:grid-cols-3"} gap-3`}>
                    <div>
                      <label className={labelClass}>Bezeichnung</label>
                      <input
                        className={inputClass}
                        value={trafo.label ?? ""}
                        onChange={(e) => updateTrafo(index, { label: e.target.value || undefined })}
                        placeholder="z.B. T1"
                      />
                    </div>
                    <div>
                      <label className={labelClass}>Sn (MVA)</label>
                      <input
                        type="number"
                        step="0.1"
                        className={inputClass}
                        value={trafo.sn_mva ?? ""}
                        onChange={(e) => updateTrafo(index, { sn_mva: Number(e.target.value) || 0 })}
                      />
                    </div>
                    <div>
                      <label className={labelClass}>Aktuelle Last (MW)</label>
                      <input
                        type="number"
                        step="0.1"
                        className={inputClass}
                        value={trafo.belastung_aktuell_mw ?? ""}
                        onChange={(e) =>
                          updateTrafo(index, {
                            belastung_aktuell_mw: e.target.value ? Number(e.target.value) : undefined,
                          })
                        }
                      />
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[22px] border border-white/10 bg-black/10 p-4">
            <div className="mb-3 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div>
                <h4 className="text-sm font-semibold text-white">Abgaenge / Reservepfade</h4>
                <p className="mt-1 text-xs leading-5 text-text-muted">
                  Nur die beste einzelne alternative Reserve wird konservativ gewertet.
                </p>
              </div>
              <button type="button" onClick={addAbgang} className={addButtonClass}>
                Abgang hinzufuegen
              </button>
            </div>

            {(umspannwerk.abgaenge ?? []).length === 0 ? (
              <p className="rounded-2xl border border-dashed border-white/10 bg-white/5 px-3 py-3 text-sm text-text-muted">
                Noch keine Abgangsdaten erfasst. Dann bleibt die explizite Reserve offen und die N-1-Stufe sinkt.
              </p>
            ) : null}

            <div className="space-y-3">
              {(umspannwerk.abgaenge ?? []).map((abgang, index) => (
                <div key={`abgang-${index}`} className="rounded-2xl border border-white/10 bg-white/5 p-3">
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div className="text-sm font-medium text-white">Abgang {index + 1}</div>
                    <button type="button" onClick={() => removeAbgang(index)} className={removeButtonClass}>
                      Entfernen
                    </button>
                  </div>

                  <div className={`mt-3 grid ${compact ? "md:grid-cols-2" : "md:grid-cols-3"} gap-3`}>
                    <div>
                      <label className={labelClass}>Bezeichnung</label>
                      <input
                        className={inputClass}
                        value={abgang.label ?? ""}
                        onChange={(e) => updateAbgang(index, { label: e.target.value || undefined })}
                        placeholder="z.B. A2"
                      />
                    </div>
                    <div>
                      <label className={labelClass}>I max (A)</label>
                      <input
                        type="number"
                        className={inputClass}
                        value={abgang.i_max_a ?? ""}
                        onChange={(e) =>
                          updateAbgang(index, { i_max_a: e.target.value ? Number(e.target.value) : undefined })
                        }
                      />
                    </div>
                    <div>
                      <label className={labelClass}>Aktuelle Last (A)</label>
                      <input
                        type="number"
                        className={inputClass}
                        value={abgang.belastung_aktuell_a ?? ""}
                        onChange={(e) =>
                          updateAbgang(index, {
                            belastung_aktuell_a: e.target.value ? Number(e.target.value) : undefined,
                          })
                        }
                      />
                    </div>
                    <div>
                      <label className={labelClass}>Explizite N-1-Reserve (A)</label>
                      <input
                        type="number"
                        className={inputClass}
                        value={abgang.reserve_n1_a ?? ""}
                        onChange={(e) =>
                          updateAbgang(index, {
                            reserve_n1_a: e.target.value ? Number(e.target.value) : undefined,
                          })
                        }
                      />
                    </div>
                    <div>
                      <label className={labelClass}>Datenquelle</label>
                      <select
                        className={selectFieldClass}
                        value={abgang.datenquelle ?? value.n1_datengrundlage ?? "planner_assumption"}
                        onChange={(e) =>
                          updateAbgang(index, { datenquelle: e.target.value as N1DataSource })
                        }
                      >
                        {DATA_SOURCE_OPTIONS.map((option) => (
                          <option key={option.value} value={option.value}>
                            {option.label}
                          </option>
                        ))}
                      </select>
                    </div>
                    <div className="flex flex-wrap gap-4 pt-1">
                      <label className="flex items-center gap-2 text-sm text-white">
                        <input
                          type="checkbox"
                          className={checkboxClass}
                          checked={Boolean(abgang.primary)}
                          onChange={(e) => updateAbgang(index, { primary: e.target.checked })}
                        />
                        Primaerer Abgang
                      </label>
                      <label className="flex items-center gap-2 text-sm text-white">
                        <input
                          type="checkbox"
                          className={checkboxClass}
                          checked={abgang.verfuegbar_im_n1 ?? true}
                          onChange={(e) => updateAbgang(index, { verfuegbar_im_n1: e.target.checked })}
                        />
                        Im N-1 verfuegbar
                      </label>
                      <label className="flex items-center gap-2 text-sm text-white">
                        <input
                          type="checkbox"
                          className={checkboxClass}
                          checked={abgang.koppelbar ?? true}
                          onChange={(e) => updateAbgang(index, { koppelbar: e.target.checked })}
                        />
                        Koppelbar
                      </label>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      <div className={sectionClass}>
        <div className="flex items-center justify-between mb-3">
          <h3 className={titleClass}>Projektkomponenten / Hybridprofil</h3>
          <button type="button" onClick={addComponent} className={addButtonClass}>
            Komponente hinzufuegen
          </button>
        </div>
        <div className="space-y-3">
          {projectComponents.length === 0 && (
            <div className="text-sm text-gray-400">
              Noch keine Komponenten erfasst. Fuer Hybrid- und Speicherprojekte sollten die Komponenten einzeln
              beschrieben werden.
            </div>
          )}
          {projectComponents.map((component, index) => (
            <div key={`${component.component_type}-${index}`} className="border border-gray-700 rounded-lg p-3 space-y-3">
              <div className="flex items-center justify-between">
                <div className="text-sm font-medium text-white">Komponente {index + 1}</div>
                <button
                  type="button"
                  onClick={() => removeComponent(index)}
                  className={removeButtonClass}
                >
                  Entfernen
                </button>
              </div>
              <div className={`grid ${compact ? "md:grid-cols-2" : "md:grid-cols-3"} gap-3`}>
                <div>
                  <label className={labelClass}>Typ</label>
                  <select
                    className={selectFieldClass}
                    value={component.component_type}
                    onChange={(e) =>
                      updateComponent(index, {
                        component_type: e.target.value as ProjectComponentInput["component_type"],
                        label: componentLabel(e.target.value as ProjectComponentInput["component_type"]),
                      })
                    }
                  >
                    <option value="pv">PV</option>
                    <option value="wind">Wind</option>
                    <option value="battery">Batteriespeicher</option>
                    <option value="charging">Ladeinfrastruktur</option>
                    <option value="heat_pump">Waermepumpe</option>
                    <option value="electrolyzer">Elektrolyseur</option>
                    <option value="substation">Umspannwerk / Schaltanlage</option>
                    <option value="load">Verbraucher / Last</option>
                    <option value="other">Sonstige</option>
                  </select>
                </div>
                <div>
                  <label className={labelClass}>Leistung (kW)</label>
                  <input
                    type="number"
                    className={inputClass}
                    value={component.capacity_kw}
                    onChange={(e) => updateComponent(index, { capacity_kw: Number(e.target.value) || 0 })}
                  />
                </div>
                <div>
                  <label className={labelClass}>Energie (kWh, optional)</label>
                  <input
                    type="number"
                    className={inputClass}
                    value={component.energy_kwh ?? ""}
                    onChange={(e) =>
                      updateComponent(index, { energy_kwh: e.target.value ? Number(e.target.value) : undefined })
                    }
                  />
                </div>
                <div>
                  <label className={labelClass}>Max. Einspeisung NAP (kW)</label>
                  <input
                    type="number"
                    className={inputClass}
                    value={component.max_export_kw ?? ""}
                    onChange={(e) =>
                      updateComponent(index, { max_export_kw: e.target.value ? Number(e.target.value) : undefined })
                    }
                  />
                </div>
                <div>
                  <label className={labelClass}>Max. Bezug NAP (kW)</label>
                  <input
                    type="number"
                    className={inputClass}
                    value={component.max_import_kw ?? ""}
                    onChange={(e) =>
                      updateComponent(index, { max_import_kw: e.target.value ? Number(e.target.value) : undefined })
                    }
                  />
                </div>
                <label className="flex items-center gap-2 text-sm text-gray-200">
                  <input
                    type="checkbox"
                    className={checkboxClass}
                    checked={Boolean(component.controllable)}
                    onChange={(e) => updateComponent(index, { controllable: e.target.checked })}
                  />
                  Steuerbar
                </label>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className={sectionClass}>
        <h3 className={titleClass}>Netzanschlusspunkt & Infrastruktur</h3>
        <div className={`grid ${compact ? "md:grid-cols-2" : "md:grid-cols-3"} gap-3`}>
          <div>
            <label className={labelClass}>Max. Einspeisung am NAP (kW)</label>
            <input
              type="number"
              className={inputClass}
              value={netzanschlusspunkt.max_export_kw ?? ""}
              onChange={(e) => patchNap({ max_export_kw: e.target.value ? Number(e.target.value) : undefined })}
            />
          </div>
          <div>
            <label className={labelClass}>Max. Bezug am NAP (kW)</label>
            <input
              type="number"
              className={inputClass}
              value={netzanschlusspunkt.max_import_kw ?? ""}
              onChange={(e) => patchNap({ max_import_kw: e.target.value ? Number(e.target.value) : undefined })}
            />
          </div>
          <div>
            <label className={labelClass}>Begrenzungskonzept</label>
            <select
              className={selectFieldClass}
              value={netzanschlusspunkt.export_limit_mode ?? "none"}
              onChange={(e) =>
                patchNap({
                  export_limit_mode: e.target.value as NetzanschlusspunktInput["export_limit_mode"],
                })
              }
            >
              <option value="none">Keine Begrenzung</option>
              <option value="fixed">Feste Begrenzung</option>
              <option value="dynamic">Dynamische Begrenzung</option>
              <option value="schedule">Fahrplan / Zeitfenster</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(netzanschlusspunkt.own_transformer)}
              onChange={(e) => patchNap({ own_transformer: e.target.checked })}
            />
            Eigener Trafo / Uebergabestation
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(netzanschlusspunkt.own_substation)}
              onChange={(e) => patchNap({ own_substation: e.target.checked })}
            />
            Eigenes Umspannwerk
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(netzanschlusspunkt.own_switchgear)}
              onChange={(e) => patchNap({ own_switchgear: e.target.checked })}
            />
            Eigenes Schaltfeld / Schaltanlage
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(netzanschlusspunkt.remote_metering_ready)}
              onChange={(e) => patchNap({ remote_metering_ready: e.target.checked })}
            />
            Fernwirk- / Messanbindung vorgesehen
          </label>
        </div>
      </div>

      <div className={sectionClass}>
        <h3 className={titleClass}>Speicher & Netzdienlichkeit</h3>
        <div className={`grid ${compact ? "md:grid-cols-2" : "md:grid-cols-3"} gap-3`}>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(storageProfile.has_storage)}
              onChange={(e) => patchStorage({ has_storage: e.target.checked })}
            />
            Speicher Bestandteil des Projekts
          </label>
          <div>
            <label className={labelClass}>Betriebsart</label>
            <select
              className={selectFieldClass}
              value={storageProfile.operation_mode ?? "unknown"}
              onChange={(e) =>
                patchStorage({
                  operation_mode: e.target.value as StorageProfileInput["operation_mode"],
                })
              }
            >
              <option value="unknown">Noch offen</option>
              <option value="market">Rein marktgetrieben</option>
              <option value="hybrid">Hybrid / gemischt</option>
              <option value="partial_grid_support">Teilweise netzdienlich</option>
              <option value="grid_support">Netzdienlich vorgesehen</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Speicherleistung (kW)</label>
            <input
              type="number"
              className={inputClass}
              value={storageProfile.power_kw ?? ""}
              onChange={(e) => patchStorage({ power_kw: e.target.value ? Number(e.target.value) : undefined })}
            />
          </div>
          <div>
            <label className={labelClass}>Speicherkapazitaet (kWh)</label>
            <input
              type="number"
              className={inputClass}
              value={storageProfile.energy_kwh ?? ""}
              onChange={(e) => patchStorage({ energy_kwh: e.target.value ? Number(e.target.value) : undefined })}
            />
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(storageProfile.remote_control_capable)}
              onChange={(e) => patchStorage({ remote_control_capable: e.target.checked })}
            />
            Fernsteuerbar
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(storageProfile.reactive_power_capable)}
              onChange={(e) => patchStorage({ reactive_power_capable: e.target.checked })}
            />
            Blindleistungsfaehig
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(storageProfile.schedule_based_dispatch)}
              onChange={(e) => patchStorage({ schedule_based_dispatch: e.target.checked })}
            />
            Fahrplanbetrieb
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(storageProfile.dynamic_export_limit)}
              onChange={(e) => patchStorage({ dynamic_export_limit: e.target.checked })}
            />
            Dynamische Einspeisebegrenzung
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(storageProfile.curtailment_ready)}
              onChange={(e) => patchStorage({ curtailment_ready: e.target.checked })}
            />
            Abregel- / Redispatch-Bereitschaft
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(storageProfile.peak_shaving)}
              onChange={(e) => patchStorage({ peak_shaving: e.target.checked })}
            />
            Peak-Shaving / Lastmanagement
          </label>
        </div>
        <p className={helperTextClass}>
          Hinweis: Netzdienliche Speicher- und Flexibilitaetskonzepte koennen die technische Bewertung und
          Abstimmungsfaehigkeit verbessern. Eine bevorzugte Behandlung ist daraus nicht ableitbar.
        </p>
      </div>

      <div className={sectionClass}>
        <h3 className={titleClass}>Umwelt & Trasse</h3>
        <div className={`grid ${compact ? "md:grid-cols-2" : "md:grid-cols-3"} gap-3`}>
          <div>
            <label className={labelClass}>Trassenlaenge (km)</label>
            <input
              type="number"
              step="0.1"
              className={inputClass}
              value={environmentalRoute.route_length_km ?? ""}
              onChange={(e) =>
                patchEnvironment({ route_length_km: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </div>
          <div>
            <label className={labelClass}>Querungen</label>
            <input
              type="number"
              className={inputClass}
              value={environmentalRoute.crossings_count ?? ""}
              onChange={(e) =>
                patchEnvironment({ crossings_count: e.target.value ? Number(e.target.value) : undefined })
              }
            />
          </div>
          <div>
            <label className={labelClass}>Trassenkomplexitaet</label>
            <select
              className={selectFieldClass}
              value={environmentalRoute.route_complexity ?? "unbekannt"}
              onChange={(e) =>
                patchEnvironment({
                  route_complexity: e.target.value as EnvironmentalRouteInput["route_complexity"],
                })
              }
            >
              <option value="unbekannt">Unbekannt</option>
              <option value="niedrig">Niedrig</option>
              <option value="mittel">Mittel</option>
              <option value="hoch">Hoch</option>
            </select>
          </div>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(environmentalRoute.protected_area_touch)}
              onChange={(e) => patchEnvironment({ protected_area_touch: e.target.checked })}
            />
            Schutzgebiet / naturschutzfachlich sensibel
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(environmentalRoute.water_protection_area)}
              onChange={(e) => patchEnvironment({ water_protection_area: e.target.checked })}
            />
            Wasserschutzthema
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(environmentalRoute.forest_crossing)}
              onChange={(e) => patchEnvironment({ forest_crossing: e.target.checked })}
            />
            Waldquerung
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(environmentalRoute.third_party_land)}
              onChange={(e) => patchEnvironment({ third_party_land: e.target.checked })}
            />
            Drittrechte / Wegerechte relevant
          </label>
          <label className="flex items-center gap-2 text-sm text-gray-200">
            <input
              type="checkbox"
              className={checkboxClass}
              checked={Boolean(environmentalRoute.noise_sensitive_area)}
              onChange={(e) => patchEnvironment({ noise_sensitive_area: e.target.checked })}
            />
            Sensibles Umfeld / Immissionskonflikt
          </label>
        </div>
      </div>
    </div>
  );
}
