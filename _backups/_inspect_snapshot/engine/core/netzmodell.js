// engine/core/netzmodell.js
// v1.1.0 - akzeptiert technicalInput-Keys vom business-to-technical Mapper.

function createSimpleGrid(input) {
    const demand      = typeof input.demand_kW === 'number' ? input.demand_kW : 0;
    const trafoCap    = typeof input.trafo_capacity_kVA === 'number' ? input.trafo_capacity_kVA : 630;
    const lineCap     = typeof input.line_capacity_kW === 'number' ? input.line_capacity_kW : 500;
    const voltage_kV  = typeof input.voltage_kV === 'number' ? input.voltage_kV : 20;
    const connectionLevel = input.connectionLevel || 'MV';

    return {
        meta: { voltage_kV, connectionLevel },
        nodes: [
            { id: 'SRC',   type: 'quelle', capacity_kW: Infinity },
            { id: 'TRAFO', type: 'trafo',  capacity_kVA: trafoCap },
            { id: 'LOAD',  type: 'last',   demand_kW: demand }
        ],
        edges: [
            { from: 'SRC',   to: 'TRAFO', capacity_kW: lineCap },
            { from: 'TRAFO', to: 'LOAD',  capacity_kW: lineCap }
        ]
    };
}

module.exports = { createSimpleGrid };


