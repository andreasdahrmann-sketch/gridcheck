import { useState } from 'react'

function App() {
  const [step, setStep] = useState(1)
  const [formData, setFormData] = useState({
    projectName: '',
    plz: '',
    leistung: '',
    anschlussart: 'Niederspannung',
    erzeugung: false,
    speicher: false
  })
  const [result, setResult] = useState(null)

  const handleChange = (e) => {
    const { name, value, type, checked } = e.target
    setFormData(prev => ({ ...prev, [name]: type === 'checkbox' ? checked : value }))
  }

  const berechne = () => {
    const leistung = parseFloat(formData.leistung)
    let machbarkeit = 'gruen'
    let hinweise = []
    let netzebene = formData.anschlussart

    if (!leistung || leistung <= 0) { alert('Bitte gueltige Leistung eingeben'); return }

    if (leistung > 300) { machbarkeit = 'rot'; hinweise.push('Leistung >300kW: Einzelfallpruefung Hoechstspannung') }
    else if (leistung > 100) { machbarkeit = 'gelb'; hinweise.push('Leistung >100kW: Mittelspannungsprüfung erforderlich'); netzebene = 'Mittelspannung' }
    else if (leistung > 30) { machbarkeit = 'gelb'; hinweise.push('Leistung >30kW: erweiterte Pruefung NS/MS'); netzebene = 'Niederspannung/Mittelspannung' }

    if (formData.erzeugung && formData.speicher) hinweise.push('Kombination Erzeugung+Speicher: Netzvertraeglichkeit pruefen')
    if (formData.erzeugung && leistung > 10) hinweise.push('Einspeiseleistung >10kW: Zertifikat nach VDE-AR-N 4105 erforderlich')

    setResult({ machbarkeit, hinweise, netzebene, leistung, timestamp: new Date().toISOString() })
    setStep(3)
  }

  const farben = { gruen: '#22c55e', gelb: '#eab308', rot: '#ef4444' }
  const labels = { gruen: 'Machbar', gelb: 'Bedingt machbar', rot: 'Kritisch' }

  return (
    <div style={{ maxWidth: 600, margin: '40px auto', fontFamily: 'Arial', padding: 20 }}>
      <h1 style={{ textAlign: 'center', color: '#1e3a5f' }}>GridCheck Pro</h1>
      <p style={{ textAlign: 'center', color: '#666' }}>Pre-Netzanschluss Diagnose</p>

      {step === 1 && (
        <div style={{ background: '#f8f9fa', padding: 24, borderRadius: 8 }}>
          <h2>Projektdaten</h2>
          <input name="projectName" placeholder="Projektname" value={formData.projectName} onChange={handleChange} style={{ width: '100%', padding: 10, marginBottom: 12, borderRadius: 4, border: '1px solid #ccc' }} />
          <input name="plz" placeholder="PLZ Standort" value={formData.plz} onChange={handleChange} style={{ width: '100%', padding: 10, marginBottom: 12, borderRadius: 4, border: '1px solid #ccc' }} />
          <input name="leistung" type="number" placeholder="Gewuenschte Leistung (kW)" value={formData.leistung} onChange={handleChange} style={{ width: '100%', padding: 10, marginBottom: 12, borderRadius: 4, border: '1px solid #ccc' }} />
          <select name="anschlussart" value={formData.anschlussart} onChange={handleChange} style={{ width: '100%', padding: 10, marginBottom: 12, borderRadius: 4, border: '1px solid #ccc' }}>
            <option>Niederspannung</option>
            <option>Mittelspannung</option>
            <option>Hochspannung</option>
          </select>
          <label style={{ display: 'block', marginBottom: 8 }}><input type="checkbox" name="erzeugung" checked={formData.erzeugung} onChange={handleChange} /> Erzeugungsanlage</label>
          <label style={{ display: 'block', marginBottom: 16 }}><input type="checkbox" name="speicher" checked={formData.speicher} onChange={handleChange} /> Speicher</label>
          <button onClick={() => setStep(2)} style={{ width: '100%', padding: 12, background: '#1e3a5f', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer', fontSize: 16 }}>Weiter zur Pruefung</button>
        </div>
      )}

      {step === 2 && (
        <div style={{ background: '#f8f9fa', padding: 24, borderRadius: 8 }}>
          <h2>Zusammenfassung</h2>
          <p><strong>Projekt:</strong> {formData.projectName}</p>
          <p><strong>PLZ:</strong> {formData.plz}</p>
          <p><strong>Leistung:</strong> {formData.leistung} kW</p>
          <p><strong>Anschluss:</strong> {formData.anschlussart}</p>
          <p><strong>Erzeugung:</strong> {formData.erzeugung ? 'Ja' : 'Nein'} | <strong>Speicher:</strong> {formData.speicher ? 'Ja' : 'Nein'}</p>
          <div style={{ display: 'flex', gap: 12 }}>
            <button onClick={() => setStep(1)} style={{ flex: 1, padding: 12, background: '#6b7280', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}>Zurueck</button>
            <button onClick={berechne} style={{ flex: 1, padding: 12, background: '#1e3a5f', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer' }}>Analyse starten</button>
          </div>
        </div>
      )}

      {step === 3 && result && (
        <div style={{ background: '#f8f9fa', padding: 24, borderRadius: 8 }}>
          <h2>Ergebnis</h2>
          <div style={{ background: farben[result.machbarkeit], color: 'white', padding: 16, borderRadius: 8, textAlign: 'center', fontSize: 20, marginBottom: 16 }}>
            {labels[result.machbarkeit]} - {result.leistung} kW
          </div>
          <p><strong>Netzebene:</strong> {result.netzebene}</p>
          {result.hinweise.length > 0 && (
            <div>
              <strong>Hinweise:</strong>
              <ul>{result.hinweise.map((h, i) => <li key={i}>{h}</li>)}</ul>
            </div>
          )}
          <p style={{ fontSize: 12, color: '#999' }}>Analyse: {result.timestamp}</p>
          <button onClick={() => { setStep(1); setResult(null) }} style={{ width: '100%', padding: 12, background: '#1e3a5f', color: 'white', border: 'none', borderRadius: 4, cursor: 'pointer', marginTop: 12 }}>Neue Analyse</button>
        </div>
      )}
    </div>
  )
}

export default App
