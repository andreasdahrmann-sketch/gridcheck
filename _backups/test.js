const { evaluateConnection } = require('./engine/decision-engine');

const input = {
    power_kW: 800,
    trafo_kVA: 630,
    line_kW: 500
};

const result = evaluateConnection(input);

console.log("=== RESULT ===");
console.log(JSON.stringify(result, null, 2));
