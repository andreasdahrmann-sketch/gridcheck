// engine/mappers/business-to-technical.js
// Mapper v1.1.0 - Business-Input -> technischer Input fuer evaluate()
// - Akzeptiert optionale technische Felder (Vorrang vor Schaetzung)
// - Dokumentiert Quelle jeder Annahme (assumptions)
// - Liefert Warnungen bei geschaetzten Werten
// - Rueckwaertskompatibel zu v1.0 (voltageLevel, assumedVoltage_kV top-level)

'use strict';

const MAPPER_VERSION = '1.1.0';

// Konservativer Reservefaktor fuer Trafo-Fallback-Schaetzung
// Deckt ab: Gleichzeitigkeit, cos phi < 1, ~15% Lastzuwachs-Puffer
// Quelle: Praxiswerte VDE-AR-N 4110 Umfeld, keine Norm-Zahl
// v1.2 geplant: lasttyp-abhaengig (Industrie 1.25, PV 1.15, Ladepark 1.35)
const TRAFO_RESERVE_FACTOR = 1.25;

const VOLTAGE_BY_LEVEL = {
  LV: 0.4,
  MV: 20,
  HV: 110
};

function mapBusinessToTechnical(businessInput) {
  const errors = [];
  const warnings = [];
  const assumptions = {};

  if (!businessInput || typeof businessInput !== 'object') {
    return {
      ok: false,
      errors: ['businessInput fehlt oder ungueltig'],
      mapperVersion: MAPPER_VERSION
    };
  }

  // ---- demand_kW ----
  let demand_kW;
  if (typeof businessInput.demand_kW === 'number') {
    demand_kW = businessInput.demand_kW;
    assumptions.demand_kW = { source: 'technical_input', value: demand_kW };
  } else if (typeof businessInput.requestedCapacityKw === 'number') {
    demand_kW = businessInput.requestedCapacityKw;
    assumptions.demand_kW = { source: 'requestedCapacityKw', value: demand_kW };
  } else {
    errors.push('demand_kW bzw. requestedCapacityKw fehlt');
  }

  // ---- voltage_kV ----
  let voltage_kV;
  if (typeof businessInput.voltage_kV === 'number') {
    voltage_kV = businessInput.voltage_kV;
    assumptions.voltage_kV = { source: 'technical_input', value: voltage_kV };
  } else if (businessInput.connectionLevel && VOLTAGE_BY_LEVEL[businessInput.connectionLevel]) {
    voltage_kV = VOLTAGE_BY_LEVEL[businessInput.connectionLevel];
    assumptions.voltage_kV = {
      source: 'connectionLevel',
      connectionLevel: businessInput.connectionLevel,
      value: voltage_kV
    };
  } else {
    errors.push('voltage_kV bzw. connectionLevel fehlt oder ungueltig');
  }

  // ---- trafo_capacity_kVA ----
  // Vorrang: explizit technisch > existingTrafoKva > Schaetzung aus estimatedAvailableCapacityKw
  let trafo_capacity_kVA;
  if (typeof businessInput.trafo_capacity_kVA === 'number') {
    trafo_capacity_kVA = businessInput.trafo_capacity_kVA;
    assumptions.trafo_capacity_kVA = { source: 'technical_input', value: trafo_capacity_kVA };
  } else if (typeof businessInput.existingTrafoKva === 'number') {
    trafo_capacity_kVA = businessInput.existingTrafoKva;
    assumptions.trafo_capacity_kVA = { source: 'existingTrafoKva', value: trafo_capacity_kVA };
  } else if (typeof businessInput.estimatedAvailableCapacityKw === 'number') {
    trafo_capacity_kVA = Math.round(businessInput.estimatedAvailableCapacityKw * TRAFO_RESERVE_FACTOR);
    assumptions.trafo_capacity_kVA = {
      source: 'estimated_from_estimatedAvailableCapacityKw',
      baseValue_kW: businessInput.estimatedAvailableCapacityKw,
      reserveFactor: TRAFO_RESERVE_FACTOR,
      value: trafo_capacity_kVA,
      note: 'Geschaetzt, keine belastbare technische Angabe. Faktor ' + TRAFO_RESERVE_FACTOR + ' deckt Gleichzeitigkeit/cos-phi/Reserve ab.'
    };
    warnings.push('trafo_capacity_kVA wurde aus estimatedAvailableCapacityKw geschaetzt (Faktor ' + TRAFO_RESERVE_FACTOR + ').');
  } else {
    errors.push('trafo_capacity_kVA nicht bestimmbar (weder technisch, noch existingTrafoKva, noch estimatedAvailableCapacityKw vorhanden)');
  }

  // ---- line_capacity_kW ----
  // Vorrang: explizit technisch > estimatedAvailableCapacityKw (1:1, konservativ)
  let line_capacity_kW;
  if (typeof businessInput.line_capacity_kW === 'number') {
    line_capacity_kW = businessInput.line_capacity_kW;
    assumptions.line_capacity_kW = { source: 'technical_input', value: line_capacity_kW };
  } else if (typeof businessInput.estimatedAvailableCapacityKw === 'number') {
    line_capacity_kW = businessInput.estimatedAvailableCapacityKw;
    assumptions.line_capacity_kW = {
      source: 'estimatedAvailableCapacityKw',
      value: line_capacity_kW,
      note: 'Annahme: angegebene verfuegbare Kapazitaet entspricht Leitungsreserve.'
    };
    warnings.push('line_capacity_kW aus estimatedAvailableCapacityKw uebernommen (Annahme, nicht validiert).');
  } else {
    errors.push('line_capacity_kW nicht bestimmbar');
  }

  if (errors.length > 0) {
    return {
      ok: false,
      errors: errors,
      warnings: warnings,
      assumptions: assumptions,
      mapperVersion: MAPPER_VERSION
    };
  }

  return {
    ok: true,
    voltageLevel: businessInput.connectionLevel || null,
    assumedVoltage_kV: voltage_kV,
    technicalInput: {
      demand_kW: demand_kW,
      voltage_kV: voltage_kV,
      trafo_capacity_kVA: trafo_capacity_kVA,
      line_capacity_kW: line_capacity_kW
    },
    assumptions: assumptions,
    warnings: warnings,
    mapperVersion: MAPPER_VERSION
  };
}

module.exports = {
  mapBusinessToTechnical: mapBusinessToTechnical,
  MAPPER_VERSION: MAPPER_VERSION,
  TRAFO_RESERVE_FACTOR: TRAFO_RESERVE_FACTOR
};

