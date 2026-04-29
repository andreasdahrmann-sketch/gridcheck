// test-evaluate.js
// Smoke-Test für engine/evaluate.js

const { evaluate } = require('./engine/evaluate');

console.log('\n=== TEST 1: Invalider Input (fehlende Pflichtfelder) ===');
const r1 = evaluate({ projectName: 'Testprojekt' });
console.log(JSON.stringify(r1, null, 2));

console.log('\n=== TEST 2: Valider Input (sollte Engine durchlaufen) ===');
const r2 = evaluate({
  projectName: 'Solarpark Nord',
  applicantName: 'Mustermann GmbH',
  connectionLevel: 'MV',
  requestedCapacityKw: 500,
  estimatedAvailableCapacityKw: 800,
  loadProfileKnown: true,
  siteSecured: true,
  // technische Felder für decision-engine:
  demand_kW: 500,
  trafo_capacity_kVA: 630,
  line_capacity_kW: 700
});
console.log(JSON.stringify(r2, null, 2));

console.log('\n=== TEST 3: Ungültiger connectionLevel ===');
const r3 = evaluate({
  projectName: 'X',
  applicantName: 'Y',
  connectionLevel: 'XYZ',
  requestedCapacityKw: 100,
  estimatedAvailableCapacityKw: 50
});
console.log(JSON.stringify(r3, null, 2));
