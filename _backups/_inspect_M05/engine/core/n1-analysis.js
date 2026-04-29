// engine/core/n1-analysis.js
// v1.1.0 - N-1 spannungsebenen-abhängig.
// NS (LV): N-1 nicht gefordert (informativ).
// MS/HS (MV/HV): N-1 gefordert, Radialnetz fällt bei Ausfall aus.

function simulateN1(grid) {
    const results = [];
    const load = grid.nodes.find(n => n.type === 'last');
    const trafo = grid.nodes.find(n => n.type === 'trafo');
    const demand = load ? load.demand_kW : 0;
    const level = grid.meta && grid.meta.connectionLevel ? grid.meta.connectionLevel : 'MV';
    const n1Required = level !== 'LV';

    // Normalbetrieb
    const trafoLoad = trafo && trafo.capacity_kVA ? demand / trafo.capacity_kVA : 0;
    const lineOverload = grid.edges.some(e => demand / e.capacity_kW > 1);
    results.push({
        case: 'normalbetrieb',
        ok: trafoLoad <= 1 && !lineOverload,
        trafoLoad
    });

    // Ausfall jeder einzelnen Leitung (radial -> Last nicht mehr versorgt)
    for (const e of grid.edges) {
        results.push({
            case: `ausfall_leitung_${e.from}-${e.to}`,
            ok: !n1Required,           // bei LV nicht gefordert => ok
            required: n1Required,
            reason: n1Required
                ? 'Radialnetz: Lastausfall bei Leitungsausfall, keine Redundanz'
                : 'N-1 auf NS-Ebene nicht gefordert'
        });
    }

    // Ausfall Trafo
    results.push({
        case: 'ausfall_trafo',
        ok: !n1Required,
        required: n1Required,
        reason: n1Required
            ? 'Einzeltrafo: kein Redundanz-Trafo vorhanden'
            : 'N-1 auf NS-Ebene nicht gefordert'
    });

    return results;
}

module.exports = { simulateN1 };
