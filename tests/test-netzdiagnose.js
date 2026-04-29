const { generateNetzdiagnose } = require("../engine/skills/gridcheck-netzdiagnose");

const mockEngineResult = {
  feasible: true,
  details: {
    capacityMarginKw: 150,
    requestedCapacityKw: 400,
    nMinusOneCapacity: 300,
    shortCircuitPowerMVA: 8,
    distanceM: 750
  }
};

console.log("=== TEST 1: DEUTSCH ===");
console.log(JSON.stringify(generateNetzdiagnose(mockEngineResult, { language: "de" }), null, 2));

console.log("\n=== TEST 2: ENGLISCH ===");
console.log(JSON.stringify(generateNetzdiagnose(mockEngineResult, { language: "en" }), null, 2));

console.log("\n=== TEST 3: FALLBACK (keine Sprache) ===");
console.log(JSON.stringify(generateNetzdiagnose(mockEngineResult, {}), null, 2));

console.log("\n=== TEST 4: NICHT MACHBAR ===");
const fail = { feasible: false, details: { capacityMarginKw: -50, requestedCapacityKw: 500, nMinusOneCapacity: 200, shortCircuitPowerMVA: 3, distanceM: 200 } };
console.log(JSON.stringify(generateNetzdiagnose(fail, { language: "de" }), null, 2));
