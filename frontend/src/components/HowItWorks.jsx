import React from 'react';

const STEPS = [
  { icon: '🛡️', title: 'Quality Gate', text: 'Blur, brightness, glare + fundus-likelihood checks reject unusable images with recapture guidance.' },
  { icon: '🎨', title: 'Preprocess', text: 'CLAHE contrast enhancement → green-channel extraction → pupil-centered crop → 512×512.' },
  { icon: '🧠', title: 'Classify', text: 'EfficientNet-B2 grades severity into the 5 ICDR stages with calibrated confidence.' },
  { icon: '🔬', title: 'Segment', text: 'U-Net (ResNet18) localizes microaneurysms, hemorrhages, exudates and cotton-wool spots.' },
  { icon: '🏥', title: 'Report', text: 'Referral urgency guidance + HL7 FHIR R4 DiagnosticReport with SNOMED CT coding.' },
];

const MODELS = [
  {
    name: 'DR Classifier',
    arch: 'EfficientNet-B2 · focal loss',
    stats: [
      ['Parameters', '8.1M'],
      ['Val accuracy', '76.7%'],
      ['ONNX latency', '77 ms'],
      ['Training data', 'IDRiD + APTOS'],
    ],
    accent: '#3b82f6',
  },
  {
    name: 'Lesion Segmenter',
    arch: 'U-Net · ResNet18 encoder',
    stats: [
      ['Parameters', '12.5M'],
      ['Val Dice', '0.21'],
      ['ONNX latency', '157 ms'],
      ['Lesion classes', 'MA · HE · EX · CWS'],
    ],
    accent: '#2ecc71',
  },
];

export default function HowItWorks() {
  return (
    <div className="how-section">
      <h2 className="section-title">How It Works</h2>

      <div className="pipeline">
        {STEPS.map((s, i) => (
          <React.Fragment key={s.title}>
            <div className="pipe-card">
              <div className="pipe-icon">{s.icon}</div>
              <div className="pipe-step">STEP {i + 1}</div>
              <h4>{s.title}</h4>
              <p>{s.text}</p>
            </div>
            {i < STEPS.length - 1 && <div className="pipe-arrow">→</div>}
          </React.Fragment>
        ))}
      </div>

      <div className="model-cards">
        {MODELS.map((m) => (
          <div key={m.name} className="card model-card" style={{ borderTopColor: m.accent }}>
            <h3>{m.name}</h3>
            <p className="small muted">{m.arch}</p>
            <table className="model-stats">
              <tbody>
                {m.stats.map(([k, v]) => (
                  <tr key={k}>
                    <td>{k}</td>
                    <td><strong>{v}</strong></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>

      <div className="card data-card">
        <h3>Trained on real clinical data</h3>
        <p>
          <strong>IDRiD</strong> (Indian Diabetic Retinopathy Image Dataset — grading labels + pixel-level lesion
          annotations) combined with <strong>APTOS 2019</strong> (3,662 graded fundus images). Models export to
          ONNX and run via onnxruntime — GPU when available, CPU fallback.
        </p>
      </div>
    </div>
  );
}
