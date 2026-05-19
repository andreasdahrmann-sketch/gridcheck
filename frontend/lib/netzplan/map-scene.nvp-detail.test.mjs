import assert from "node:assert/strict";
import test from "node:test";

/**
 * Mirrors buildNvpCapacityDetail in map-scene.ts for a dependency-free smoke test.
 * Keep in sync when compliance wording changes.
 */
function buildNvpCapacityDetail(result) {
  if (result.n1.dso_daten_vorhanden && result.nvp_freie_kapazitaet_kw > 0) {
    return `Vom Netzbetreiber gemeldete Kapazitaetsangabe: ${result.nvp_freie_kapazitaet_kw} kW`;
  }
  if (result.nvp_freie_kapazitaet_kw > 0) {
    return `Eingabe-/Screeningwert ${result.nvp_freie_kapazitaet_kw} kW – keine verifizierte freie Netzkapazitaet`;
  }
  return "Keine verifizierte freie Netzkapazitaet; OSM liefert keine Kapazitaetsaussage.";
}

test("buildNvpCapacityDetail without DSO data never claims verified free capacity", () => {
  const detail = buildNvpCapacityDetail({
    n1: { dso_daten_vorhanden: false },
    nvp_freie_kapazitaet_kw: 500,
  });
  assert.match(detail, /keine verifizierte freie Netzkapazitaet/i);
  assert.doesNotMatch(detail, /gemeldete Kapazitaetsangabe/i);
});

test("buildNvpCapacityDetail with DSO data uses operator wording", () => {
  const detail = buildNvpCapacityDetail({
    n1: { dso_daten_vorhanden: true },
    nvp_freie_kapazitaet_kw: 1200,
  });
  assert.match(detail, /Netzbetreiber gemeldete/i);
});
