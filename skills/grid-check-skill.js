// skills/grid-check-skill.js
// v2.1.0 - Pre-Netzanschluss-Check Skill
// Nutzt ausschliesslich das revisionssichere Public Interface engine/evaluate.js

const fs = require('fs');
const path = require('path');
const { evaluate, ENGINE_VERSION } = require('../engine/evaluate');

const SKILL_VERSION = '2.1.0';
const SKILL_NAME = 'pre-grid-connection-check';

function runGridCheck(input) {
    const startedAt = new Date().toISOString();
    const raw = evaluate(input);

    const result = {
        skill: {
            name: SKILL_NAME,
            version: SKILL_VERSION,
            engineVersion: ENGINE_VERSION,
            startedAt,
            finishedAt: new Date().toISOString()
        },
        status: raw.status,
        summary: buildSummary(raw),
        details: {
            validation: raw.validation || null,
            mapping: raw.mapping || null,
            engine: raw.result || null,
            error: raw.error || null,
            reason: raw.reason || null
        },
        revision: raw.meta || null
    };

    return result;
}

function buildSummary(raw) {
    const s = {
        verdict: raw.status,
        headline: '',
        blockers: [],
        warnings: [],
        recommendations: [],
        keyFigures: {}
    };

    if (raw.status === 'rejected') {
        s.headline = `Eingabe abgelehnt (${raw.reason || 'unbekannt'})`;
        if (raw.validation && Array.isArray(raw.validation.errors)) {
            s.blockers = raw.validation.errors.map(e => ({
                code: e.code || 'VALIDATION',
                message: e.message || JSON.stringify(e)
            }));
        }
        return s;
    }
    if (raw.status === 'error') {
        s.headline = 'Interner Fehler bei der Bewertung';
        s.blockers.push({
            code: 'ENGINE_EXCEPTION',
            message: raw.error && raw.error.message ? raw.error.message : 'Unbekannter Fehler'
        });
        return s;
    }

    const eng = raw.result || {};
    s.blockers = eng.blockers || [];
    s.warnings = eng.warnings || [];
    s.recommendations = eng.recommendations || [];

    const diag = eng.diagnostics || {};
    s.keyFigures = {
        trafoLoad_pct: diag.trafoLoad != null ? +(diag.trafoLoad * 100).toFixed(1) : null,
        maxLineLoad_pct: Array.isArray(diag.lineLoads) && diag.lineLoads.length
            ? +(Math.max(...diag.lineLoads.map(l => l.load)) * 100).toFixed(1)
            : null,
        n1Required: !!diag.n1Required,
        n1ViolationCount: diag.n1ViolationCount || 0,
        voltageLevel: raw.mapping ? raw.mapping.voltageLevel : null
    };

    switch (raw.status) {
        case 'feasible':
            s.headline = 'Netzanschluss technisch machbar';
            break;
        case 'conditional':
            s.headline = 'Netzanschluss bedingt machbar (Auflagen erforderlich)';
            break;
        case 'not_feasible':
            s.headline = 'Netzanschluss so nicht machbar';
            break;
        default:
            s.headline = `Status: ${raw.status}`;
    }

    return s;
}

function formatReport(result) {
    const L = [];
    const iconMap = {
        feasible: '[OK]',
        conditional: '[!]',
        not_feasible: '[X]',
        rejected: '[STOP]',
        error: '[ERR]'
    };
    const icon = iconMap[result.status] || '[?]';

    L.push('===========================================================');
    L.push(`  PRE-NETZANSCHLUSS-CHECK  -  ${result.skill.name} v${result.skill.version}`);
    L.push(`  Engine: v${result.skill.engineVersion}   Zeitpunkt: ${result.skill.finishedAt}`);
    L.push('===========================================================');
    L.push('');
    L.push(`${icon} ${result.summary.headline.toUpperCase()}`);
    L.push(`   Status: ${result.status}`);
    L.push('');

    const kf = result.summary.keyFigures || {};
    if (Object.keys(kf).length) {
        L.push('-- Kennzahlen ---------------------------------------------');
        if (kf.voltageLevel)            L.push(`   Spannungsebene:      ${kf.voltageLevel}`);
        if (kf.trafoLoad_pct != null)   L.push(`   Trafo-Auslastung:    ${kf.trafoLoad_pct} %`);
        if (kf.maxLineLoad_pct != null) L.push(`   Max. Leitungslast:   ${kf.maxLineLoad_pct} %`);
        L.push(`   N-1 erforderlich:    ${kf.n1Required ? 'ja' : 'nein'}`);
        if (kf.n1Required)              L.push(`   N-1 Verletzungen:    ${kf.n1ViolationCount}`);
        L.push('');
    }

    if (result.summary.blockers.length) {
        L.push('-- Blocker ------------------------------------------------');
        result.summary.blockers.forEach(b => {
            const code = b.code || 'BLOCKER';
            const msg = b.message || JSON.stringify(b);
            L.push(`   [X] [${code}] ${msg}`);
        });
        L.push('');
    }
    if (result.summary.warnings.length) {
        L.push('-- Warnungen ----------------------------------------------');
        result.summary.warnings.forEach(w => L.push(`   [!] ${typeof w === 'string' ? w : JSON.stringify(w)}`));
        L.push('');
    }
    if (result.summary.recommendations.length) {
        L.push('-- Empfehlungen -------------------------------------------');
        result.summary.recommendations.forEach(r => L.push(`   [i] ${typeof r === 'string' ? r : JSON.stringify(r)}`));
        L.push('');
    }

    if (result.revision) {
        L.push('-- Revisionsdaten -----------------------------------------');
        L.push(`   inputHash:          ${result.revision.inputHash || '-'}`);
        L.push(`   technicalInputHash: ${result.revision.technicalInputHash || '-'}`);
        L.push(`   rulesVersion:       ${result.revision.rulesVersion || '-'}`);
        L.push(`   mapperVersion:      ${result.revision.mapperVersion || '-'}`);
        L.push(`   engineVersion:      ${result.revision.engineVersion || '-'}`);
        L.push('');
    }

    L.push('===========================================================');
    return L.join('\n');
}

if (require.main === module) {
    const args = process.argv.slice(2);
    const jsonOnly = args.includes('--json');
    const fileArg = args.find(a => !a.startsWith('--'));

    if (!fileArg) {
        console.error('Usage: node skills/grid-check-skill.js <input.json> [--json]');
        process.exit(2);
    }

    const filePath = path.resolve(fileArg);
    if (!fs.existsSync(filePath)) {
        console.error(`Datei nicht gefunden: ${filePath}`);
        process.exit(2);
    }

    let input;
    try {
        input = JSON.parse(fs.readFileSync(filePath, 'utf8'));
    } catch (e) {
        console.error(`Ungueltiges JSON in ${filePath}: ${e.message}`);
        process.exit(2);
    }

    const result = runGridCheck(input);

    if (jsonOnly) {
        console.log(JSON.stringify(result, null, 2));
    } else {
        console.log(formatReport(result));
    }

    const exitCodes = { feasible: 0, conditional: 0, not_feasible: 1, rejected: 2, error: 3 };
    const code = exitCodes[result.status];
    process.exit(code === undefined ? 4 : code);
}

module.exports = { runGridCheck, formatReport, SKILL_VERSION, SKILL_NAME };
