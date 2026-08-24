import React, { useState } from 'react';
import Upload from './components/Upload';
import Results from './components/Results';
import BatchScreening from './components/BatchScreening';
import HowItWorks from './components/HowItWorks';

const TABS = [
  { id: 'single', label: 'Screening' },
  { id: 'batch', label: 'Batch Mode' },
  { id: 'about', label: 'How It Works' },
];

export default function App() {
  const [tab, setTab] = useState('single');
  const [prediction, setPrediction] = useState(null);
  const [meta, setMeta] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [patientId, setPatientId] = useState('PT-0001');

  const openResult = (result, url, latency) => {
    setPrediction(result);
    setPreviewUrl(url || null);
    setMeta(latency !== undefined ? { latencyMs: latency } : null);
    setTab('single');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNewAnalysis = () => {
    setPrediction(null);
    setPreviewUrl(null);
    setMeta(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">
          <span className="logo-icon">◉</span>
          <div>
            <h1>RetinaScan AI</h1>
            <p>AI-Based Diabetic Retinopathy Screening &amp; Classification</p>
          </div>
        </div>
        <div className="header-meta">
          <span className="badge badge-blue">ICDR 5-Stage</span>
          <span className="badge badge-green">FHIR R4</span>
          {prediction && (
            <button className="btn btn-outline" onClick={handleNewAnalysis}>
              New Analysis
            </button>
          )}
        </div>
      </header>

      <nav className="tabs">
        {TABS.map((t) => (
          <button
            key={t.id}
            className={`tab ${tab === t.id ? 'active' : ''}`}
            onClick={() => setTab(t.id)}
          >
            {t.label}
          </button>
        ))}
      </nav>

      <main className="app-main">
        {tab === 'single' &&
          (prediction ? (
            <Results result={prediction} meta={meta} previewUrl={previewUrl} patientId={patientId} />
          ) : (
            <Upload
              onResult={(res, latency) => {
                setPrediction(res);
                setMeta(latency !== undefined ? { latencyMs: latency } : null);
              }}
              previewUrl={previewUrl}
              setPreviewUrl={setPreviewUrl}
              patientId={patientId}
              setPatientId={setPatientId}
            />
          ))}

        {tab === 'batch' && !prediction && (
          <BatchScreening onOpenResult={openResult} />
        )}
        {tab === 'batch' && prediction && (
          <Results result={prediction} meta={meta} previewUrl={previewUrl} patientId={patientId} />
        )}

        {tab === 'about' && <HowItWorks />}
      </main>

      <footer className="app-footer">
        <span>Smart India Hackathon 2026 · SIH26038 · Decision support only — not a substitute for clinical diagnosis</span>
      </footer>
    </div>
  );
}
