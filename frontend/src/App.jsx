import React, { useState } from 'react';
import Upload from './components/Upload';
import Results from './components/Results';

export default function App() {
  const [prediction, setPrediction] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [patientId, setPatientId] = useState('PT-0001');

  const handleNewAnalysis = () => {
    setPrediction(null);
    setPreviewUrl(null);
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

      <main className="app-main">
        {!prediction ? (
          <Upload
            onResult={setPrediction}
            previewUrl={previewUrl}
            setPreviewUrl={setPreviewUrl}
            patientId={patientId}
            setPatientId={setPatientId}
          />
        ) : (
          <Results result={prediction} patientId={patientId} />
        )}
      </main>

      <footer className="app-footer">
        <span>Smart India Hackathon 2026 · SIH26038 · Decision support only — not a substitute for clinical diagnosis</span>
      </footer>
    </div>
  );
}
