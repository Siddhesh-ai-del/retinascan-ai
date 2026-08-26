import React, { useState } from 'react';
import { RotateCcw } from 'lucide-react';
import Upload from './components/Upload';
import Results from './components/Results';
import BatchScreening from './components/BatchScreening';
import HowItWorks from './components/HowItWorks';

const TABS = [
  { id: 'single', label: 'Screening' },
  { id: 'batch', label: 'Batch Mode' },
  { id: 'about', label: 'How It Works' },
];

function LogoMark() {
  return (
    <svg
      className="logo-mark"
      width="40"
      height="40"
      viewBox="0 0 40 40"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.5"
      aria-hidden="true"
    >
      <path d="M4 20c4.5-7.5 10-11.2 16-11.2S31.5 12.5 36 20c-4.5 7.5-10 11.2-16 11.2S8.5 27.5 4 20Z" />
      <circle cx="20" cy="20" r="6.2" />
      <circle cx="20" cy="20" r="2" fill="currentColor" stroke="none" />
      <line x1="20" y1="2.5" x2="20" y2="8" />
    </svg>
  );
}

export default function App() {
  const [tab, setTab] = useState('single');
  const [prediction, setPrediction] = useState(null);
  const [attentionB64, setAttentionB64] = useState(null);
  const [meta, setMeta] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [patientId, setPatientId] = useState('PT-0001');

  const openResult = (result, url, latency) => {
    if (previewUrl && previewUrl !== url) URL.revokeObjectURL(previewUrl);
    setPrediction(result);
    setPreviewUrl(url || null);
    setAttentionB64(null);
    setMeta(latency !== undefined ? { latencyMs: latency } : null);
    setTab('single');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNewAnalysis = () => {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPrediction(null);
    setPreviewUrl(null);
    setMeta(null);
    setAttentionB64(null);
  };

  return (
    <div className="app">
      <header className="app-header">
        <div className="logo">
          <LogoMark />
          <div>
            <h1>RetinaScan AI</h1>
            <p>Diabetic Retinopathy Screening</p>
          </div>
        </div>
        <div className="header-meta">
          <span className="meta-tag accent">ICDR 5-Stage</span>
          <span className="meta-tag">FHIR R4</span>
          {prediction && (
            <button className="btn btn-outline" onClick={handleNewAnalysis}>
              <RotateCcw size={14} strokeWidth={2} />
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
            <Results result={prediction} meta={meta} patientId={patientId} attention={attentionB64} />
          ) : (
            <Upload
              onResult={(res, latency) => {
                setPrediction(res);
                setMeta(latency !== undefined ? { latencyMs: latency } : null);
              }}
              onAttention={setAttentionB64}
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
          <Results result={prediction} meta={meta} patientId={patientId} attention={attentionB64} />
        )}

        {tab === 'about' && <HowItWorks />}
      </main>

      <footer className="app-footer">
        Smart India Hackathon 2026 · SIH26038 · Decision support only — not a substitute for clinical diagnosis
      </footer>
    </div>
  );
}
