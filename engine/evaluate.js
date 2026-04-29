// engine/evaluate.js
// Revisionssicherer Wrapper: Validierung + Mapping + Engine + Meta-Daten
// v1.2.0 - Drei-Wege-Status (feasible | conditional | not_feasible)

const fs = require('fs');
const path = require('path');
const crypto = require('crypto');

const InputValidator = require('./validators/input-validation');
const { mapBusinessToTechnical, MAPPER_VERSION } = require('./mappers/business-to-technical');
const { evaluateConnection } = require('./decision-engine');

const ENGINE_VERSION = '1.2.0';

// Rules einmalig laden
const rulesPath = path.join(__dirname, '..', 'rules', 'input-validation.rules.json');
const rules = JSON.parse(fs.readFileSync(rulesPath, 'utf8'));
const validator = new InputValidator(rules);

function evaluate(input) {
  const timestamp = new Date().toISOString();

  // Hash des Business-Inputs für Revisionssicherheit
  const inputHash = crypto
    .createHash('sha256')
    .update(JSON.stringify(input || {}))
    .digest('hex');

  const baseMeta = {
    timestamp,
    engineVersion: ENGINE_VERSION,
    mapperVersion: MAPPER_VERSION,
    inputHash
  };

  // 1. Input-Validierung (Business-Ebene)
  const validation = validator.validate(input);

  if (!validation.valid) {
    return {
      status: 'rejected',
      reason: 'input_validation_failed',
      validation,
      meta: { ...baseMeta, rulesVersion: validation.rulesVersion }
    };
  }

  // 2. Business -> Technical Mapping
  const mapping = mapBusinessToTechnical(input);

  if (!mapping.ok) {
    return {
      status: 'rejected',
      reason: 'mapping_failed',
      validation,
      mapping,
      meta: { ...baseMeta, rulesVersion: validation.rulesVersion }
    };
  }

  const technicalInput = mapping.technicalInput;

  const technicalInputHash = crypto
    .createHash('sha256')
    .update(JSON.stringify(technicalInput))
    .digest('hex');

  // 3. Technische Engine-Bewertung
  let engineResult;
  try {
    engineResult = evaluateConnection(technicalInput);
  } catch (err) {
    return {
      status: 'error',
      reason: 'engine_exception',
      error: { message: err.message, stack: err.stack },
      validation,
      mapping,
      meta: {
        ...baseMeta,
        rulesVersion: validation.rulesVersion,
        technicalInputHash
      }
    };
  }

  // 4. Revisionssicheres Gesamtergebnis
  // Status-Mapping: Engine liefert feasible | conditional | not_feasible
  // Gesamt-Status übernimmt Engine-Status 1:1 (konsistente Drei-Wege-Logik)
  const overallStatus = engineResult.status
    || (engineResult.feasible ? 'feasible' : 'not_feasible');

  return {
    status: overallStatus,
    validation,
    mapping: {
      voltageLevel: mapping.voltageLevel,
      assumedVoltage_kV: mapping.assumedVoltage_kV,
      technicalInput: mapping.technicalInput,
      assumptions: mapping.assumptions,
      warnings: mapping.warnings,
      mapperVersion: mapping.mapperVersion
    },
    result: engineResult,
    meta: {
      ...baseMeta,
      rulesVersion: validation.rulesVersion,
      technicalInputHash
    }
  };
}

module.exports = { evaluate, ENGINE_VERSION };
