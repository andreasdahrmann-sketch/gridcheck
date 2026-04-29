const { t } = require("./i18n/resolver");
const SKILL = "netzdiagnose";

function generateNetzdiagnose(engineResult, input = {}) {
  const d = engineResult.details || {};
  const lang = (input.language || "de").toLowerCase();

  const diagnosis = {
    summary: "",
    gridAssessment: "",
    n1Assessment: "",
    stabilityAssessment: "",
    keyRisks: [],
    recommendations: [],
    meta: {
      skill: "gridcheck-netzdiagnose",
      version: "1.2.0",
      language: lang,
      timestamp: new Date().toISOString()
    }
  };

  // Grid Capacity
  if (d.capacityMarginKw >= 0) {
    diagnosis.gridAssessment = t(SKILL, lang, "gridOk");
  } else {
    diagnosis.gridAssessment = t(SKILL, lang, "gridInsufficient");
    diagnosis.keyRisks.push(t(SKILL, lang, "riskCapacityDeficit"));
  }

  // N-1
  const n1Ok = d.requestedCapacityKw <= d.nMinusOneCapacity;
  if (n1Ok) {
    diagnosis.n1Assessment = t(SKILL, lang, "n1Ok");
  } else {
    diagnosis.n1Assessment = t(SKILL, lang, "n1Failed");
    diagnosis.keyRisks.push(t(SKILL, lang, "riskN1"));
    diagnosis.recommendations.push(t(SKILL, lang, "recN1"));
  }

  // Stability
  if (d.shortCircuitPowerMVA >= 5) {
    diagnosis.stabilityAssessment = t(SKILL, lang, "stabilityOk");
  } else {
    diagnosis.stabilityAssessment = t(SKILL, lang, "stabilityCritical");
    diagnosis.keyRisks.push(t(SKILL, lang, "riskShortCircuit"));
  }

  // Distance
  if (d.distanceM > 500) {
    diagnosis.keyRisks.push(t(SKILL, lang, "riskDistance"));
    diagnosis.recommendations.push(t(SKILL, lang, "recDistance"));
  }

  // Summary (sprachunabhängige Logik über n1Ok-Flag!)
  if (engineResult.feasible && !n1Ok) {
    diagnosis.summary = t(SKILL, lang, "summaryFeasibleNoN1");
  } else if (engineResult.feasible) {
    diagnosis.summary = t(SKILL, lang, "summaryFeasible");
  } else {
    diagnosis.summary = t(SKILL, lang, "summaryNotFeasible");
  }

  return diagnosis;
}

module.exports = { generateNetzdiagnose };
