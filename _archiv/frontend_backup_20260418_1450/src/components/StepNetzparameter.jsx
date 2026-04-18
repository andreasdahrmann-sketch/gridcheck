// C:\Users\andre\gridcheck\frontend\src\components\StepNetzparameter.jsx
export default function StepNetzparameter({ data, updateData, onBack, onSubmit, loading }) {
  const valid = data.trafo_mva && data.leitungslaenge_km;

  const inputClass = "w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors";
  const labelClass = "block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2";
  const selectClass = "w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors appearance-none";

  return (
    <div className="space-y-8">
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Netzparameter</h2>
        <p className="text-gray-400">Technische Daten des Netzanschlusspunkts</p>
      </div>

      {/* Transformator & Netz */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 space-y-6">
        <h3 className="text-lg font-semibold text-emerald-400 flex items-center gap-2">
          <span>🔌</span> Netzanschluss
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className={labelClass}>Netzverknüpfungspunkt</label>
            <input className={inputClass} placeholder="z.B. UW Musterstadt"
              value={data.netzverknuepfungspunkt} onChange={e => updateData({ netzverknuepfungspunkt: e.target.value })} />
          </div>
          <div>
            <label className={labelClass}>Kurzschlussleistung Sk'' (MVA)</label>
            <input className={inputClass} type="number" placeholder="z.B. 250"
              value={data.skv_mva} onChange={e => updateData({ skv_mva: e.target.value })} />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className={labelClass}>Trafo-Leistung (MVA) *</label>
            <input className={inputClass} type="number" step="0.1" placeholder="z.B. 40"
              value={data.trafo_mva} onChange={e => updateData({ trafo_mva: e.target.value })} />
          </div>
          <div>
            <label className={labelClass}>Vorbelastung am NVP (MW)</label>
            <input className={inputClass} type="number" placeholder="z.B. 12"
              value={data.vorbelastung_mw} onChange={e => updateData({ vorbelastung_mw: e.target.value })} />
          </div>
        </div>
      </div>

      {/* Leitung */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 space-y-6">
        <h3 className="text-lg font-semibold text-emerald-400 flex items-center gap-2">
          <span>🔗</span> Leitungsparameter
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className={labelClass}>Leitungslänge (km) *</label>
            <input className={inputClass} type="number" step="0.1" placeholder="z.B. 3.5"
              value={data.leitungslaenge_km} onChange={e => updateData({ leitungslaenge_km: e.target.value })} />
          </div>
          <div>
            <label className={labelClass}>Netztyp</label>
            <select className={selectClass} value={data.netz_typ}
              onChange={e => updateData({ netz_typ: e.target.value })}>
              <option value="kabel">Kabel</option>
              <option value="freileitung">Freileitung</option>
            </select>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className={labelClass}>Leitungstyp</label>
            <select className={selectClass} value={data.leitungstyp}
              onChange={e => updateData({ leitungstyp: e.target.value })}>
              <option value="NAYY">NAYY (Alu)</option>
              <option value="NYY">NYY (Kupfer)</option>
              <option value="NA2XS2Y">NA2XS2Y (VPE)</option>
              <option value="AL/ST">AL/ST 185 (Freileitung)</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Querschnitt (mm²)</label>
            <select className={selectClass} value={data.querschnitt_mm2}
              onChange={e => updateData({ querschnitt_mm2: e.target.value })}>
              <option value="95">95 mm²</option>
              <option value="150">150 mm²</option>
              <option value="185">185 mm²</option>
              <option value="240">240 mm²</option>
              <option value="300">300 mm²</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Parallelsysteme</label>
            <select className={selectClass} value={data.parallelsysteme}
              onChange={e => updateData({ parallelsysteme: e.target.value })}>
              <option value="1">1</option>
              <option value="2">2</option>
              <option value="3">3</option>
            </select>
          </div>
        </div>
      </div>

      {/* Eigentumsgrenze */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6">
        <h3 className="text-lg font-semibold text-emerald-400 flex items-center gap-2 mb-4">
          <span>📍</span> Eigentumsgrenze
        </h3>
        <div className="flex gap-4">
          {['HAK', 'Übergabestation', 'Schaltanlage NB'].map(opt => (
            <button key={opt} onClick={() => updateData({ eigentumsgrenze: opt })}
              className={`px-4 py-2 rounded-lg border text-sm font-medium transition-all ${
                data.eigentumsgrenze === opt
                  ? 'border-emerald-500 bg-emerald-900/30 text-emerald-400'
                  : 'border-gray-700 bg-gray-800 text-gray-400 hover:border-gray-600'
              }`}>
              {opt}
            </button>
          ))}
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-between">
        <button onClick={onBack}
          className="px-6 py-3 rounded-lg font-semibold text-gray-400 border border-gray-700 hover:border-gray-600 hover:text-white transition-all">
          ← Zurück
        </button>
        <button onClick={onSubmit} disabled={!valid || loading}
          className={`px-8 py-3 rounded-lg font-semibold text-white transition-all flex items-center gap-3 ${
            valid && !loading
              ? 'bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-900/30'
              : 'bg-gray-700 cursor-not-allowed opacity-50'
          }`}>
          {loading ? (
            <>
              <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none"/>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
              </svg>
              Analyse läuft...
            </>
          ) : '🔍 Analyse starten'}
        </button>
      </div>
    </div>
  );
}
