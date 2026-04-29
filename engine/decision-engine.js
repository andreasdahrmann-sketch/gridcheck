// engine/decision-engine.js
// v1.2.0 - differenzierte Bewertung: feasible / conditional / not_feasible
// Schnittstelle bleibt: evaluateConnection(technicalInput) -> { feasible, ... }

const { createSimpleGrid } = require('./core/netzmodell');
const { simulateN1 } = require('./core/n1-analysis');

const ENGINE_CORE_VERSION = '1.2.0';

function evaluateConnection(input) {
    const grid = createSimpleGrid(input);
    const n1Results = simulateN1(grid);

    const load  = grid.nodes.find(n => n.type === 'last');
    const trafo = grid.nodes.find(n => n.type === 'trafo');
    const lines = grid.edges;

    const demand = load.demand_kW;
    const level  = grid.meta.connectionLevel;

    const trafoLoad = trafo.capacity_kVA > 0 ? demand / trafo.capacity_kVA : Infinity;
    const lineLoads = lines.map(l => ({
        id: `${l.from}-${l.to}`,
        load: l.capacity_kW > 0 ? demand / l.capacity_kW : Infinity
    }));

    const blockers = [];
    const warnings = [];
    const recommendations = [];

    // --- Normalbetrieb: Trafo ---
    if (trafoLoad > 1) {
        blockers.push({
            code: 'TRAFO_OVERLOAD',
            message: `Trafo überlastet (${(trafoLoad * 100).toFixed(0)} %)`
        });
        const requiredTrafo = Math.ceil(demand * 1.2);
        recommendations.push(`Trafo auf mindestens ${requiredTrafo} kVA erhöhen (inkl. 20 % Reserve)`);
    } else if (trafoLoad > 0.8) {
        warnings.push(`Trafo-Auslastung hoch (${(trafoLoad * 100).toFixed(0)} %) - wenig Reserve`);
    }

    // --- Normalbetrieb: Leitungen ---
    for (const l of lineLoads) {
        if (l.load > 1) {
            blockers.push({
                code: 'LINE_OVERLOAD',
                message: `Leitung ${l.id} überlastet (${(l.load * 100).toFixed(0)} %)`
            });
            recommendations.push(`Leitung ${l.id} verstärken oder parallelen Strang vorsehen`);
        } else if (l.load > 0.8) {
            warnings.push(`Leitung ${l.id} stark ausgelastet (${(l.load * 100).toFixed(0)} %)`);
        }
    }

    // --- N-1 Bewertung (nur wenn gefordert) ---
    const n1Required = level !== 'LV';
    const n1Violations = n1Results.filter(r => r.case !== 'normalbetrieb' && r.required === true && r.ok === false);

    if (n1Required && n1Violations.length > 0) {
        warnings.push(`N-1 Kriterium auf ${level}-Ebene nicht erfüllt (${n1Violations.length} Ausfallszenarien)`);
        recommendations.push('Redundante Einspeisung, Ringstruktur oder zweiten Trafo prüfen');
    }

    // --- Gesamtstatus ---
    // feasible: keine Blocker, keine N-1-Verletzung
    // conditional: keine Blocker, aber N-1-Verletzung auf MV/HV
    // not_feasible: Blocker vorhanden (Normalbetrieb überlastet)
    let status;
    if (blockers.length > 0) {
        status = 'not_feasible';
    } else if (n1Required && n1Violations.length > 0) {
        status = 'conditional';
    } else {
        status = 'feasible';
    }

    const feasible = status === 'feasible';

    return {
        feasible,
        status,
        grid,
        n1Results,
        diagnostics: {
            trafoLoad,
            lineLoads,
            n1Required,
            n1ViolationCount: n1Violations.length,
            engineCoreVersion: ENGINE_CORE_VERSION
        },
        blockers,
        warnings,
        recommendations
    };
}

module.exports = { evaluateConnection, ENGINE_CORE_VERSION };
