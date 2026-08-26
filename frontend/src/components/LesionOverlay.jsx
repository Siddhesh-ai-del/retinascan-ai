import React, { useEffect, useState } from 'react';

export default function LesionOverlay({ segmentation, attention }) {
  const allOn = (seg) => Object.fromEntries((seg?.legend || []).map((l) => [l.key, true]));
  const [active, setActive] = useState(() => allOn(segmentation));
  const [showAttention, setShowAttention] = useState(false);

  /* New analysis result → reset every lesion toggle to visible. */
  useEffect(() => {
    setActive(allOn(segmentation));
    setShowAttention(false);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [segmentation]);

  const toggle = (key) => setActive((a) => ({ ...a, [key]: !a[key] }));

  if (!segmentation || !segmentation.original) return <p className="muted">Segmentation unavailable.</p>;

  const { original, overlays, legend = [], lesions = {} } = segmentation;

  return (
    <div className="overlay-wrap">
      <h3>Lesion Segmentation</h3>
      <div className="overlay-canvas">
        <img src={`data:image/png;base64,${original}`} alt="Fundus" className="layer" />
        {legend.map(
          (l) =>
            active[l.key] &&
            overlays?.[l.key] && (
              <img
                key={l.key}
                src={`data:image/png;base64,${overlays[l.key]}`}
                alt={l.name}
                className="layer"
              />
            )
        )}
        {showAttention && attention && (
          <img src={`data:image/png;base64,${attention}`} alt="AI attention heatmap" className="layer" />
        )}
      </div>

      <div className="legend">
        {legend.map((l) => {
          const info = lesions[l.key] || {};
          return (
            <label key={l.key} className={`legend-item ${active[l.key] ? '' : 'off'}`}>
              <input type="checkbox" checked={active[l.key]} onChange={() => toggle(l.key)} />
              <span className="dot" style={{ background: l.color }} />
              <span className="legend-name">{l.name}</span>
              <span className="legend-status">{info.detected ? 'detected' : '—'}</span>
            </label>
          );
        })}
        {attention && (
          <label className={`legend-item ${showAttention ? '' : 'off'}`}>
            <input type="checkbox" checked={showAttention} onChange={() => setShowAttention((s) => !s)} />
            <span
              className="dot"
              style={{ background: 'linear-gradient(90deg, #1a237e, #29b6f6, #ffee58, #d32f2f)' }}
            />
            <span className="legend-name">AI Attention</span>
            <span className="legend-status">Grad-CAM</span>
          </label>
        )}
      </div>
    </div>
  );
}
