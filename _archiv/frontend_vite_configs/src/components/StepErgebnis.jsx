// C:\Users\andre\gridcheck\frontend\src\components\StepErgebnis.jsx
export default function StepErgebnis({ result, data, onBack, onReset }) {
  const r = result;
  const ampelColor = {
    grün: 'emerald', gelb: 'yellow', rot: 'red'
  }[r.ampel] || 'gray';

  const ampelLabels = {
    grün: 'Anschluss möglich',
    gelb: 'Anschluss mit Auflagen möglich',
    rot: 'Anschluss kritisch'
  };

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Analyseergebnis</h2>
        <p className="text-gray-400">{data.projektname} — {data.leistung_kw} kW {data.anlagentyp.toUpperCase()}</p>
      </div>

      {/* Ampel-Status */}
      <div className={`border rounded-xl p-6 bg-${ampelColor}-900/20 border-${ampelColor}-800`}>
        <div className="flex items-center gap-4">
          <div className={`w-16 h-16 rounded-full bg-${ampelColor}-500 flex items-center justify-center text-2xl shadow-lg shadow-${ampelColor}-900/50`}>
            {r.ampel === 'grün' ? '✅' : r.ampel === 'gelb' ? '⚠️' : '❌'}
          </div>
          <div>
            <h3 className={`text-xl font-bold text-${ampelColor}-400`}>
              {ampelLabels[r.ampel] || r.ampel}
            </h3>
            <p className="text-gray-400 text-sm mt-1">
              Netzverträglichkeitsindex: <span className="text-white font-semibold">{r.netzvertraeglichkeits_index}/100</span>
            </p>
          </div>
        </div>
      </div>

      {/* Technische Ergebnisse */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-emerald-400 mb-4">📊 Technische Ergebnisse</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          {[
            { label: 'Therm. Auslastung', value: `${r.thermische_auslastung_prozent?.toFixed(1)}%`, warn: r.thermische_auslastung_prozent > 100 },
            { label: 'Spg.-Anhebung', value: `${r.spannungsanhebung_prozent?.toFixed(2)}%`, warn: r.spannungsanhebung_prozent > 2 },
            { label: 'Verlustleistung', value: `${r.verlustleistung_kw?.toFixed(1)} kW` },
            { label: 'Max. Einspeiseleistung', value: `${(r.max_einspeiseleistung_kw / 1000)?.toFixed(1)} MW` },
          ].map((item, i) => (
            <div key={i} className={`p-4 rounded-lg border ${item.warn ? 'bg-red-900/20 border-red-800' : 'bg-gray-800/50 border-gray-700'}`}>
              <p className="text-xs text-gray-500 uppercase">{item.label}</p>
              <p className={`text-xl font-bold mt-1 ${item.warn ? 'text-red-400' : 'text-white'}`}>{item.value}</p>
            </div>
          ))}
        </div>
      </div>

      {/* N-1 Analyse */}
      {r.n1_piegel && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-emerald-400 mb-4">🔒 N-1 Sicherheitsanalyse</h3>
          <div className="grid grid-cols-2 gap-4">
            <div className={`p-4 rounded-lg border ${r.n1_piegel.n1_bestanden ? 'bg-emerald-900/20 border-emerald-800' : 'bg-red-900/20 border-red-800'}`}>
              <p className="text-xs text-gray-500 uppercase">N-1 Status</p>
              <p className={`text-lg font-bold mt-1 ${r.n1_piegel.n1_bestanden ? 'text-emerald-400' : 'text-red-400'}`}>
                {r.n1_piegel.n1_bestanden ? '✅ Bestanden' : '❌ Nicht bestanden'}
              </p>
            </div>
            <div className="p-4 rounded-lg border border-gray-700 bg-gray-800/50">
              <p className="text-xs text-gray-500 uppercase">Auslastung bei N-1</p>
              <p className="text-lg font-bold mt-1 text-white">{r.n1_piegel.auslastung_n1_prozent?.toFixed(1)}%</p>
            </div>
          </div>
        </div>
      )}

      {/* Empfehlungen */}
      {r.empfehlungen?.length > 0 && (
        <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
          <h3 className="text-lg font-semibold text-emerald-400 mb-4">💡 Empfehlungen</h3>
          <div className="space-y-3">
            {r.empfehlungen.map((emp, i) => (
              <div key={i} className="flex items-start gap-3 p-3 bg-gray-800/50 rounded-lg">
                <span className="text-emerald-400 mt-0.5">→</span>
                <span className="text-gray-300 text-sm">{emp}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Navigation */}
      <div className="flex justify-between">
        <button onClick={onBack}
          className="px-6 py-3 rounded-lg font-semibold text-gray-400 border border-gray-700 hover:border-gray-600 hover:text-white transition-all">
          ← Parameter anpassen
        </button>
        <div className="flex gap-3">
          <button onClick={() => window.print()}
            className="px-6 py-3 rounded-lg font-semibold text-gray-300 border border-gray-700 hover:border-gray-600 transition-all">
            🖨️ PDF Export
          </button>
          <button onClick={onReset}
            className="px-6 py-3 rounded-lg font-semibold text-white bg-emerald-600 hover:bg-emerald-500 transition-all">
            🔄 Neue Analyse
          </button>
        </div>
      </div>
    </div>
  );
}

