// C:\Users\andre\gridcheck\frontend\src\App.jsx
import { useState, useEffect } from 'react';
import StepProjekt from './components/StepProjekt';
import StepNetzparameter from './components/StepNetzparameter';
import StepErgebnis from './components/StepErgebnis';

const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export default function App() {
  const [step, setStep] = useState(1);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [data, setData] = useState({
    projektname: '', plz: '', anlagentyp: 'pv', leistung_kw: '', spannungsebene: '20',
    cos_phi: '0.95', einspeiseart: 'volleinspeisung', speicher: false, speicher_kwh: '',
    koordinaten_lat: '', koordinaten_lon: '', inbetriebnahme: '', kontakt_name: '',
    kontakt_email: '', kontakt_firma: '',
    trafo_mva: '', leitungslaenge_km: '', leitungstyp: 'NAYY', querschnitt_mm2: '150',
    netzverknuepfungspunkt: '', skv_mva: '', parallelsysteme: '1', eigentumsgrenze: 'HAK',
    vorbelastung_mw: '', netz_typ: 'kabel',
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [history, setHistory] = useState([]);

  useEffect(() => {
    fetch(`${API}/api/history`).then(r => r.json()).then(setHistory).catch(() => {});
  }, [result]);

  const updateData = (fields) => setData(prev => ({ ...prev, ...fields }));

  const runAnalysis = async () => {
    setLoading(true);
    setError('');
    try {
      const payload = {
        projektname: data.projektname,
        plz: data.plz,
        anlagentyp: data.anlagentyp,
        leistung_kw: parseFloat(data.leistung_kw),
        spannungsebene: data.spannungsebene,
        cos_phi: parseFloat(data.cos_phi),
        einspeiseart: data.einspeiseart,
        speicher: data.speicher,
        speicher_kwh: data.speicher ? parseFloat(data.speicher_kwh) || 0 : 0,
        koordinaten_lat: parseFloat(data.koordinaten_lat) || null,
        koordinaten_lon: parseFloat(data.koordinaten_lon) || null,
        inbetriebnahme: data.inbetriebnahme || null,
        trafo_mva: parseFloat(data.trafo_mva),
        leitungslaenge_km: parseFloat(data.leitungslaenge_km),
        leitungstyp: data.leitungstyp,
        querschnitt_mm2: parseFloat(data.querschnitt_mm2),
        netzverknuepfungspunkt: data.netzverknuepfungspunkt || null,
        skv_mva: parseFloat(data.skv_mva) || null,
        parallelsysteme: parseInt(data.parallelsysteme),
        eigentumsgrenze: data.eigentumsgrenze,
        vorbelastung_mw: parseFloat(data.vorbelastung_mw) || 0,
        netz_typ: data.netz_typ,
      };
      const res = await fetch(`${API}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Analyse fehlgeschlagen');
      }
      const r = await res.json();
      setResult(r);
      setStep(3);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const reset = () => {
    setStep(1);
    setResult(null);
    setError('');
    setData({
      projektname: '', plz: '', anlagentyp: 'pv', leistung_kw: '', spannungsebene: '20',
      cos_phi: '0.95', einspeiseart: 'volleinspeisung', speicher: false, speicher_kwh: '',
      koordinaten_lat: '', koordinaten_lon: '', inbetriebnahme: '', kontakt_name: '',
      kontakt_email: '', kontakt_firma: '',
      trafo_mva: '', leitungslaenge_km: '', leitungstyp: 'NAYY', querschnitt_mm2: '150',
      netzverknuepfungspunkt: '', skv_mva: '', parallelsysteme: '1', eigentumsgrenze: 'HAK',
      vorbelastung_mw: '', netz_typ: 'kabel',
    });
  };

  const loadFromHistory = (h) => {
    setData(prev => ({
      ...prev,
      projektname: h.projektname || '',
      leistung_kw: String(h.leistung_kw || ''),
      anlagentyp: h.anlagentyp || 'pv',
      plz: h.plz || '',
    }));
    setStep(1);
  };

  const stepsMeta = [
    { id: 1, label: 'Projektdaten', icon: '\u{1F4CB}' },
    { id: 2, label: 'Netzparameter', icon: '\u26A1' },
    { id: 3, label: 'Ergebnis', icon: '\u{1F4CA}' },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-white flex">
      {/* Sidebar */}
      <aside className={`${sidebarOpen ? 'w-64' : 'w-16'} bg-gray-900 border-r border-gray-800 flex flex-col transition-all duration-300 shrink-0`}>
        {/* Logo */}
        <div className="p-4 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-emerald-600 rounded-lg flex items-center justify-center text-white font-black text-lg">G</div>
            {sidebarOpen && (
              <div>
                <h1 className="text-lg font-black text-white leading-none">GridCheck</h1>
                <span className="text-[10px] text-emerald-400 font-semibold">PRO v2.0</span>
              </div>
            )}
          </div>
        </div>

        {/* Nav Steps */}
        <nav className="flex-1 p-3 space-y-1">
          {stepsMeta.map(s => (
            <button key={s.id}
              onClick={() => s.id <= step && setStep(s.id)}
              disabled={s.id > step}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                step === s.id
                  ? 'bg-emerald-600/20 text-emerald-400 border border-emerald-600/30'
                  : s.id < step
                    ? 'text-gray-400 hover:bg-gray-800 cursor-pointer'
                    : 'text-gray-600 cursor-not-allowed'
              }`}>
              <span className="text-lg">{s.icon}</span>
              {sidebarOpen && <span>{s.label}</span>}
              {s.id < step && sidebarOpen && <span className="ml-auto text-emerald-500 text-xs">{'\u2713'}</span>}
            </button>
          ))}
        </nav>

        {/* History in Sidebar */}
        {sidebarOpen && history.length > 0 && (
          <div className="p-3 border-t border-gray-800">
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2 px-2">Letzte Analysen</p>
            <div className="space-y-1 max-h-48 overflow-y-auto">
              {history.slice(0, 5).map((h, i) => (
                <button key={i} onClick={() => loadFromHistory(h)}
                  className="w-full text-left px-2 py-1.5 rounded text-xs text-gray-400 hover:bg-gray-800 hover:text-white transition-colors truncate">
                  <span className={`inline-block w-2 h-2 rounded-full mr-2 ${
                    h.score >= 80 ? 'bg-green-500' : h.score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                  }`} />
                  {h.projektname} ({h.leistung_kw} kW)
                </button>
              ))}
            </div>
          </div>
        )}

        {/* Sidebar Toggle */}
        <button onClick={() => setSidebarOpen(!sidebarOpen)}
          className="p-3 border-t border-gray-800 text-gray-500 hover:text-white text-xs transition-colors">
          {sidebarOpen ? '\u25C0 Einklappen' : '\u25B6'}
        </button>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-h-screen">
        {/* Top Bar */}
        <header className="h-14 bg-gray-900/50 border-b border-gray-800 flex items-center justify-between px-6 backdrop-blur-sm">
          <div className="flex items-center gap-4">
            <span className="text-sm text-gray-500">
              Schritt {step} von 3
            </span>
            <span className="text-xs text-gray-700">|</span>
            <span className="text-sm text-gray-400">{stepsMeta[step - 1].icon} {stepsMeta[step - 1].label}</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-xs px-2 py-1 bg-emerald-900/30 text-emerald-400 rounded border border-emerald-800">BETA</span>
            <span className="text-xs text-gray-600">Revisionssicher | VDE-konform</span>
          </div>
        </header>

        {/* Content */}
        <main className="flex-1 p-8 overflow-y-auto">
          <div className="max-w-4xl mx-auto">
            {/* Progress Bar */}
            <div className="mb-8">
              <div className="h-1 bg-gray-800 rounded-full overflow-hidden">
                <div className="h-full bg-gradient-to-r from-emerald-600 to-emerald-400 rounded-full transition-all duration-500"
                  style={{ width: `${(step / 3) * 100}%` }} />
              </div>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-900/20 border border-red-800 rounded-lg flex items-center gap-3">
                <span className="text-red-400 text-lg">{'\u274C'}</span>
                <div className="flex-1">
                  <p className="text-red-400 font-medium">Fehler bei der Analyse</p>
                  <p className="text-red-400/70 text-sm">{error}</p>
                </div>
                <button onClick={() => setError('')} className="text-red-400 hover:text-red-300">{'\u2715'}</button>
              </div>
            )}

            {step === 1 && (
              <StepProjekt data={data} updateData={updateData} onNext={() => setStep(2)} />
            )}
            {step === 2 && (
              <StepNetzparameter data={data} updateData={updateData}
                onBack={() => setStep(1)} onSubmit={runAnalysis} loading={loading} />
            )}
            {step === 3 && result && (
              <StepErgebnis result={result} data={data} onBack={() => setStep(2)} onReset={reset} />
            )}
          </div>
        </main>
      </div>
    </div>
  );
}

