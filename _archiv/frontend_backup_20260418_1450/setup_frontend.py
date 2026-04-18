import os

def w(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True) if os.path.dirname(path) else None
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f'OK {path}')

# === StepNetzparameter.jsx ===
w('src/components/StepNetzparameter.jsx', r"""import { useState } from 'react';

export default function StepNetzparameter({ data, onNext, onBack }) {
  const [form, setForm] = useState({
    netztyp: data.netztyp || 'Strahlennetz',
    entfernung_ums_km: data.entfernung_ums_km || '',
    trafo_leistung_mva: data.trafo_leistung_mva || '',
    skv_mva: data.skv_mva || '',
    bestehende_einspeisung_kw: data.bestehende_einspeisung_kw || '0',
    leitungstyp: data.leitungstyp || 'NAYY 150',
    leitungslaenge_km: data.leitungslaenge_km || '',
  });

  const handleChange = (e) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = () => {
    if (!form.entfernung_ums_km || !form.trafo_leistung_mva) {
      alert('Bitte alle Pflichtfelder ausfuellen');
      return;
    }
    onNext(form);
  };

  return (
    <div>
      <h2 className="text-xl font-bold text-blue-400 mb-6">Netzparameter</h2>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-xs text-gray-400 uppercase tracking-wide mb-1">Netztyp *</label>
          <select name="netztyp" value={form.netztyp} onChange={handleChange}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none">
            <option value="Strahlennetz">Strahlennetz</option>
            <option value="Ringnetz">Ringnetz</option>
            <option value="Maschennetz">Maschennetz</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-gray-400 uppercase tracking-wide mb-1">Entfernung zum UW (km) *</label>
          <input type="number" step="0.1" name="entfernung_ums_km" value={form.entfernung_ums_km} onChange={handleChange}
            placeholder="z.B. 5.2"
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none" />
        </div>

        <div>
          <label className="block text-xs text-gray-400 uppercase tracking-wide mb-1">Trafo-Leistung (MVA) *</label>
          <input type="number" step="0.1" name="trafo_leistung_mva" value={form.trafo_leistung_mva} onChange={handleChange}
            placeholder="z.B. 40"
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none" />
        </div>

        <div>
          <label className="block text-xs text-gray-400 uppercase tracking-wide mb-1">Kurzschlussleistung Skv (MVA)</label>
          <input type="number" step="0.1" name="skv_mva" value={form.skv_mva} onChange={handleChange}
            placeholder="z.B. 250 (optional)"
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none" />
          <p className="text-xs text-gray-500 mt-1">Falls unbekannt, wird geschaetzt</p>
        </div>

        <div>
          <label className="block text-xs text-gray-400 uppercase tracking-wide mb-1">Bestehende Einspeisung (kW)</label>
          <input type="number" name="bestehende_einspeisung_kw" value={form.bestehende_einspeisung_kw} onChange={handleChange}
            placeholder="0"
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none" />
        </div>

        <div>
          <label className="block text-xs text-gray-400 uppercase tracking-wide mb-1">Leitungstyp</label>
          <select name="leitungstyp" value={form.leitungstyp} onChange={handleChange}
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white focus:border-blue-500 focus:outline-none">
            <option value="NAYY 150">NAYY 150mm²</option>
            <option value="NAYY 240">NAYY 240mm²</option>
            <option value="NA2XS2Y 150">NA2XS2Y 150mm²</option>
            <option value="NA2XS2Y 240">NA2XS2Y 240mm²</option>
            <option value="Al/St 240/40">Freileitung Al/St 240/40</option>
          </select>
        </div>

        <div>
          <label className="block text-xs text-gray-400 uppercase tracking-wide mb-1">Leitungslaenge (km)</label>
          <input type="number" step="0.1" name="leitungslaenge_km" value={form.leitungslaenge_km} onChange={handleChange}
            placeholder="z.B. 3.5"
            className="w-full bg-gray-700 border border-gray-600 rounded-lg px-4 py-3 text-white placeholder-gray-500 focus:border-blue-500 focus:outline-none" />
        </div>
      </div>

      <div className="flex justify-between mt-8">
        <button onClick={onBack}
          className="px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg text-white transition-colors">
          Zurueck
        </button>
        <button onClick={handleSubmit}
          className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold transition-colors">
          Analyse starten 🚀
        </button>
      </div>
    </div>
  );
}
""")

# === StepErgebnis.jsx ===
w('src/components/StepErgebnis.jsx', r"""import { useState, useEffect } from 'react';

function ScoreGauge({ score }) {
  const color = score >= 80 ? '#22c55e' : score >= 50 ? '#eab308' : '#ef4444';
  const label = score >= 80 ? 'ANSCHLUSS MACHBAR' : score >= 50 ? 'BEDINGT MACHBAR' : 'KRITISCH';
  const circumference = 2 * Math.PI * 54;
  const offset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col items-center">
      <svg width="140" height="140" className="transform -rotate-90">
        <circle cx="70" cy="70" r="54" stroke="#374151" strokeWidth="12" fill="none" />
        <circle cx="70" cy="70" r="54" stroke={color} strokeWidth="12" fill="none"
          strokeDasharray={circumference} strokeDashoffset={offset}
          strokeLinecap="round" className="transition-all duration-1000" />
      </svg>
      <div className="relative -mt-24 flex flex-col items-center">
        <span className="text-3xl font-bold text-white">{score}</span>
        <span className="text-xs text-gray-400">/ 100</span>
      </div>
      <div className="mt-6 px-4 py-1 rounded-full text-sm font-bold" style={{ backgroundColor: color + '22', color }}>
        {label}
      </div>
    </div>
  );
}

function CheckItem({ label, ok, detail }) {
  return (
    <div className={`flex items-center justify-between p-3 rounded-lg ${ok ? 'bg-green-900/20 border border-green-800' : 'bg-red-900/20 border border-red-800'}`}>
      <div className="flex items-center gap-2">
        <span className="text-lg">{ok ? '✅' : '❌'}</span>
        <span className="text-white font-medium">{label}</span>
      </div>
      <span className="text-sm text-gray-400">{detail}</span>
    </div>
  );
}

function NetzplanSimple({ data }) {
  return (
    <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
      <h3 className="text-sm font-bold text-gray-400 uppercase mb-3">Vereinfachter Netzplan</h3>
      <div className="flex items-center justify-center gap-2 text-sm">
        <div className="bg-blue-900 border border-blue-600 rounded px-3 py-2 text-center">
          <div className="text-blue-400 font-bold">UW</div>
          <div className="text-xs text-gray-400">{data.skv_mva || '~250'} MVA</div>
        </div>
        <div className="text-gray-500">---[{data.leitungslaenge_km || '?'} km]---</div>
        <div className="bg-purple-900 border border-purple-600 rounded px-3 py-2 text-center">
          <div className="text-purple-400 font-bold">Trafo</div>
          <div className="text-xs text-gray-400">{data.trafo_leistung_mva} MVA</div>
        </div>
        <div className="text-gray-500">---[{data.entfernung_ums_km} km]---</div>
        <div className="bg-green-900 border border-green-600 rounded px-3 py-2 text-center">
          <div className="text-green-400 font-bold">VAP</div>
          <div className="text-xs text-gray-400">{data.leistung_kw} kW</div>
        </div>
      </div>
      <div className="text-center mt-2 text-xs text-gray-500">Netztyp: {data.netztyp} | {data.leitungstyp}</div>
    </div>
  );
}

export default function StepErgebnis({ data, onBack, onReset }) {
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const run = async () => {
      try {
        const payload = {
          name: data.name,
          plz: data.plz,
          typ: data.typ,
          leistung_kw: parseFloat(data.leistung_kw),
          spannung_kv: data.spannung_kv ? parseFloat(data.spannung_kv) : 20,
          cos_phi: parseFloat(data.cos_phi) || 0.95,
          einspeiseart: data.einspeiseart || 'Volleinspeisung',
          netztyp: data.netztyp,
          entfernung_ums_km: parseFloat(data.entfernung_ums_km),
          trafo_leistung_mva: parseFloat(data.trafo_leistung_mva),
          skv_mva: data.skv_mva ? parseFloat(data.skv_mva) : null,
          bestehende_einspeisung_kw: parseFloat(data.bestehende_einspeisung_kw) || 0,
          leitungstyp: data.leitungstyp,
          leitungslaenge_km: data.leitungslaenge_km ? parseFloat(data.leitungslaenge_km) : null,
        };
        const res = await fetch('http://127.0.0.1:8000/api/check', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(payload),
        });
        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || 'API Fehler');
        }
        const json = await res.json();
        setResult(json);
      } catch (e) {
        setError(e.message);
      } finally {
        setLoading(false);
      }
    };
    run();
  }, []);

  if (loading) return (
    <div className="flex flex-col items-center justify-center py-20">
      <div className="animate-spin rounded-full h-16 w-16 border-t-2 border-b-2 border-blue-500 mb-4"></div>
      <p className="text-gray-400">Netzanalyse laeuft...</p>
      <p className="text-xs text-gray-600 mt-2">Spannungsband | Thermik | Kurzschluss | N-1</p>
    </div>
  );

  if (error) return (
    <div className="text-center py-10">
      <p className="text-red-400 text-lg mb-4">Fehler: {error}</p>
      <button onClick={onBack} className="px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg text-white">Zurueck</button>
    </div>
  );

  const r = result;

  return (
    <div>
      <h2 className="text-xl font-bold text-blue-400 mb-6">Ergebnis: {data.name}</h2>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Score */}
        <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 flex justify-center">
          <ScoreGauge score={r.score} />
        </div>

        {/* Checks */}
        <div className="lg:col-span-2 space-y-3">
          <CheckItem label="Spannungsband (+-10%)" ok={r.spannungsband_ok}
            detail={r.details?.delta_u_percent ? `ΔU = ${r.details.delta_u_percent.toFixed(2)}%` : ''} />
          <CheckItem label="Thermische Auslastung" ok={r.thermische_auslastung_ok}
            detail={r.details?.auslastung_prozent ? `${r.details.auslastung_prozent.toFixed(1)}%` : ''} />
          <CheckItem label="Kurzschlussfestigkeit" ok={r.kurzschluss_ok}
            detail={r.details?.ikss_ka ? `Ik = ${r.details.ikss_ka.toFixed(2)} kA` : ''} />
          <CheckItem label="(N-1)-Sicherheit" ok={r.n1_ok}
            detail={r.n1_ok ? 'Redundanz gegeben' : 'Keine Redundanz'} />
        </div>
      </div>

      {/* Netzplan */}
      <div className="mt-6">
        <NetzplanSimple data={data} />
      </div>

      {/* Netzebene & Empfehlung */}
      <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-bold text-gray-400 uppercase mb-2">Netzebene</h3>
          <p className="text-white text-lg">{r.netzebene}</p>
        </div>
        <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-bold text-gray-400 uppercase mb-2">Empfehlung</h3>
          <p className="text-white">{r.empfehlung}</p>
        </div>
      </div>

      {/* Details */}
      {r.details && (
        <div className="mt-6 bg-gray-800 rounded-lg p-4 border border-gray-700">
          <h3 className="text-sm font-bold text-gray-400 uppercase mb-2">Berechnungsdetails</h3>
          <pre className="text-xs text-gray-300 overflow-auto">{JSON.stringify(r.details, null, 2)}</pre>
        </div>
      )}

      {/* Audit-Hinweis */}
      <div className="mt-4 text-xs text-gray-600 text-center">
        Revisionssicher gespeichert | Projekt-ID: {r.project_id} | Checksum im Audit-Log
      </div>

      <div className="flex justify-between mt-8">
        <button onClick={onBack} className="px-6 py-3 bg-gray-700 hover:bg-gray-600 rounded-lg text-white transition-colors">
          Zurueck
        </button>
        <button onClick={onReset} className="px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg text-white font-semibold transition-colors">
          Neue Analyse
        </button>
      </div>
    </div>
  );
}
""")

# === Updated App.jsx with all 3 steps ===
w('src/App.jsx', r"""import { useState, useEffect } from 'react';
import StepProjekt from './components/StepProjekt';
import StepNetzparameter from './components/StepNetzparameter';
import StepErgebnis from './components/StepErgebnis';

const STEPS = ['Projekt', 'Netzparameter', 'Ergebnis'];

export default function App() {
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState({});
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetch('http://127.0.0.1:8000/api/projects')
      .then(r => r.json())
      .then(setHistory)
      .catch(() => {});
  }, [step]);

  const handleStep1Next = (data) => {
    setFormData({ ...formData, ...data });
    setStep(1);
  };

  const handleStep2Next = (data) => {
    setFormData({ ...formData, ...data });
    setStep(2);
  };

  const handleReset = () => {
    setFormData({});
    setStep(0);
  };

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <header className="bg-gray-800 border-b border-gray-700 px-6 py-4">
        <div className="max-w-5xl mx-auto flex justify-between items-center">
          <div>
            <h1 className="text-xl font-bold text-green-400">⚡ GridCheck Pro</h1>
            <p className="text-xs text-gray-500">Netzanschluss Pre-Check v2.0</p>
          </div>
          <span className="bg-red-600 text-xs px-2 py-1 rounded font-bold">BETA</span>
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {/* Stepper */}
        <div className="flex gap-2 mb-8">
          {STEPS.map((s, i) => (
            <div key={i} className={`flex-1 text-center py-3 rounded-lg text-sm font-medium transition-all
              ${i === step ? 'bg-blue-600 text-white' : i < step ? 'bg-green-900 text-green-400 border border-green-700' : 'bg-gray-800 text-gray-500 border border-gray-700'}`}>
              {i < step ? '✓' : `${i + 1}.`} {s}
            </div>
          ))}
        </div>

        {/* Content */}
        <div className="bg-gray-800 rounded-xl p-8 border border-gray-700 shadow-2xl">
          {step === 0 && <StepProjekt data={formData} onNext={handleStep1Next} />}
          {step === 1 && <StepNetzparameter data={formData} onNext={handleStep2Next} onBack={() => setStep(0)} />}
          {step === 2 && <StepErgebnis data={formData} onBack={() => setStep(1)} onReset={handleReset} />}
        </div>

        {/* History */}
        {history.length > 0 && step === 0 && (
          <div className="mt-8">
            <h3 className="text-sm font-bold text-gray-400 mb-3">📋 Letzte Berechnungen</h3>
            <div className="space-y-2">
              {history.slice(0, 5).map(p => (
                <div key={p.id} className="bg-gray-800 rounded-lg p-3 border border-gray-700 flex justify-between items-center">
                  <div>
                    <span className="text-white font-medium">{p.name}</span>
                    <span className="text-gray-500 text-sm ml-3">{p.leistung_kw} kW | {p.typ}</span>
                  </div>
                  <span className="text-xs text-gray-600">{p.plz}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
""")

print("FERTIG - Frontend komplett")
