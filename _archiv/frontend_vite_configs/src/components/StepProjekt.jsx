// C:\Users\andre\gridcheck\frontend\src\components\StepProjekt.jsx
export default function StepProjekt({ data, updateData, onNext }) {
  const valid = data.projektname && data.plz && data.leistung_kw;

  const inputClass = "w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors";
  const labelClass = "block text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2";
  const selectClass = "w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-3 text-white focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500 outline-none transition-colors appearance-none";

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h2 className="text-2xl font-bold text-white mb-2">Projektdaten erfassen</h2>
        <p className="text-gray-400">Grundlegende Informationen zu Ihrem Einspeiseprojekt</p>
      </div>

      {/* Projekt Grunddaten */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 space-y-6">
        <h3 className="text-lg font-semibold text-emerald-400 flex items-center gap-2">
          <span>📋</span> Grunddaten
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className={labelClass}>Projektname *</label>
            <input className={inputClass} placeholder="z.B. Solarpark Musterstadt"
              value={data.projektname} onChange={e => updateData({ projektname: e.target.value })} />
          </div>
          <div>
            <label className={labelClass}>PLZ *</label>
            <input className={inputClass} placeholder="12345" maxLength={5}
              value={data.plz} onChange={e => updateData({ plz: e.target.value.replace(/\D/g, '') })} />
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className={labelClass}>Anlagentyp *</label>
            <select className={selectClass} value={data.anlagentyp}
              onChange={e => updateData({ anlagentyp: e.target.value })}>
              <option value="pv">☀️ Photovoltaik</option>
              <option value="wind">💨 Wind</option>
              <option value="biogas">🌿 Biogas</option>
              <option value="bess">🔋 Batteriespeicher</option>
              <option value="kwk">⚡ KWK</option>
              <option value="wasser">💧 Wasserkraft</option>
              <option value="last">🏭 Großverbraucher</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Anschlussleistung (kW) *</label>
            <input className={inputClass} type="number" placeholder="z.B. 5000"
              value={data.leistung_kw} onChange={e => updateData({ leistung_kw: e.target.value })} />
          </div>
        </div>
      </div>

      {/* Technische Parameter */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 space-y-6">
        <h3 className="text-lg font-semibold text-emerald-400 flex items-center gap-2">
          <span>⚡</span> Technische Parameter
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className={labelClass}>Spannungsebene</label>
            <select className={selectClass} value={data.spannungsebene}
              onChange={e => updateData({ spannungsebene: e.target.value })}>
              <option value="0.4">0,4 kV (NS)</option>
              <option value="20">20 kV (MS)</option>
              <option value="110">110 kV (HS)</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>cos φ</label>
            <input className={inputClass} type="number" step="0.01" min="0.8" max="1"
              value={data.cos_phi} onChange={e => updateData({ cos_phi: e.target.value })} />
            <p className="text-xs text-gray-600 mt-1">Standard: 0,95 (VDE-AR-N 4110)</p>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div>
            <label className={labelClass}>Einspeiseart</label>
            <select className={selectClass} value={data.einspeiseart}
              onChange={e => updateData({ einspeiseart: e.target.value })}>
              <option value="volleinspeisung">Volleinspeisung</option>
              <option value="ueberschuss">Überschusseinspeisung</option>
              <option value="nulleinspeisung">Nulleinspeisung</option>
            </select>
          </div>
          <div>
            <label className={labelClass}>Geplante Inbetriebnahme</label>
            <input className={inputClass} type="date"
              value={data.inbetriebnahme} onChange={e => updateData({ inbetriebnahme: e.target.value })} />
          </div>
        </div>

        {/* Speicher Toggle */}
        <div className="flex items-center gap-4 p-4 bg-gray-800/50 rounded-lg">
          <label className="relative inline-flex items-center cursor-pointer">
            <input type="checkbox" className="sr-only peer" checked={data.speicher}
              onChange={e => updateData({ speicher: e.target.checked })} />
            <div className="w-11 h-6 bg-gray-700 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-emerald-600"></div>
          </label>
          <span className="text-gray-300">Batteriespeicher vorhanden</span>
          {data.speicher && (
            <input className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white w-32 ml-auto"
              type="number" placeholder="kWh"
              value={data.speicher_kwh} onChange={e => updateData({ speicher_kwh: e.target.value })} />
          )}
        </div>
      </div>

      {/* Kontakt (optional) */}
      <div className="bg-gray-900/50 border border-gray-800 rounded-xl p-6 space-y-6">
        <h3 className="text-lg font-semibold text-gray-500 flex items-center gap-2">
          <span>👤</span> Kontaktdaten <span className="text-xs font-normal">(optional)</span>
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <label className={labelClass}>Name</label>
            <input className={inputClass} placeholder="Max Mustermann"
              value={data.kontakt_name} onChange={e => updateData({ kontakt_name: e.target.value })} />
          </div>
          <div>
            <label className={labelClass}>E-Mail</label>
            <input className={inputClass} type="email" placeholder="max@firma.de"
              value={data.kontakt_email} onChange={e => updateData({ kontakt_email: e.target.value })} />
          </div>
          <div>
            <label className={labelClass}>Firma</label>
            <input className={inputClass} placeholder="Firma GmbH"
              value={data.kontakt_firma} onChange={e => updateData({ kontakt_firma: e.target.value })} />
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex justify-end">
        <button onClick={onNext} disabled={!valid}
          className={`px-8 py-3 rounded-lg font-semibold text-white transition-all ${valid
            ? 'bg-emerald-600 hover:bg-emerald-500 shadow-lg shadow-emerald-900/30'
            : 'bg-gray-700 cursor-not-allowed opacity-50'}`}>
          Weiter → Netzparameter
        </button>
      </div>
    </div>
  );
}
