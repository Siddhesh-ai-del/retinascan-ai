import React, { useState } from 'react';

export default function LesionOverlay({ segmentation }) {
  const [active, setActive] = useState(() =>
    Object.fromEntries((segmentation.legend || []).map((l) => [l.key, true]))
  );

  const toggle = (key) => setActive((a) => ({ ...a, [key]: !a[key] }));

  if (!segmentation || !segmentation.original) return <p className="muted">Segmentation unavailable.</p>;

  const { original, overlays, legend, lesions } = segmentation;

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
      </div>
    </div>
  );
}
