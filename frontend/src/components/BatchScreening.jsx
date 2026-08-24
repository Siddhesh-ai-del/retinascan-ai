import React, { useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
const STAGE_COLORS = ['#2ecc71', '#a3e635', '#f59e0b', '#f97316', '#ef4444'];

export default function BatchScreening({ onOpenResult }) {
  const [queue, setQueue] = useState([]);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(0);

  const runAll = async (files) => {
    const items = Array.from(files).map((f) => ({
      file: f,
      name: f.name,
      status: 'queued',
      result: null,
    }));
    setQueue(items);
    setRunning(true);
    setDone(0);

    for (let i = 0; i < items.length; i++) {
      setQueue((q) => q.map((x, j) => (j === i ? { ...x, status: 'running' } : x)));
      const form = new FormData();
      form.append('file', items[i].file);
      try {
        const res = await axios.post(`${API_URL}/api/predict?patient_id=batch`, form, { timeout: 120000 });
        items[i].result = res.data;
        items[i].status = res.data.status === 'rejected' ? 'rejected' : 'ok';
      } catch (err) {
        items[i].status = 'error';
        items[i].result = null;
      }
      items[i].previewUrl = URL.createObjectURL(items[i].file);
      const snapshot = [...items];
      setQueue(snapshot);
      setDone(i + 1);
    }
    setRunning(false);
  };

  const sorted = [...queue].sort((a, b) => {
    const sa = a.result?.classification?.stage ?? -1;
    const sb = b.result?.classification?.stage ?? -1;
    return sb - sa;
  });

  return (
    <div className="batch-section">
      <label className="dropzone batch-drop">
        <input
          type="file"
          accept="image/*"
          multiple
          hidden
          disabled={running}
          onChange={(e) => e.target.files.length && runAll(e.target.files)}
        />
        <div className="dropzone-empty">
          <div className="dropzone-icon">🗂️</div>
          <h2>{running ? `Screening ${done}/${queue.length}…` : 'Select multiple fundus images'}</h2>
          <p>batch screening · sorted by severity</p>
        </div>
      </label>

      {running && (
        <div className="batch-progress-track">
          <div className="batch-progress-fill" style={{ width: `${(done / Math.max(queue.length, 1)) * 100}%` }} />
        </div>
      )}

      {queue.some((q) => q.status !== 'queued' && q.status !== 'running') > 0 && (
        <table className="batch-table card">
          <thead>
            <tr>
              <th></th>
              <th>Patient image</th>
              <th>ICDR stage</th>
              <th>Confidence</th>
              <th>Referral</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {sorted.map((item) => {
              const c = item.result?.classification;
              const ref = item.result?.referral;
              return (
                <tr key={item.name + item.previewUrl}>
                  <td>
                    {item.previewUrl && <img src={item.previewUrl} alt="" className="row-thumb" />}
                  </td>
                  <td className="row-name">{item.name}</td>
                  <td>
                    {c ? (
                      <span className="stage-chip" style={{ background: STAGE_COLORS[c.stage] }}>
                        {c.stage} · {c.label}
                      </span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>{c ? `${(c.confidence * 100).toFixed(0)}%` : '—'}</td>
                  <td className="small">{ref ? (ref.recommended ? `⚠ ${ref.urgency}` : 'routine') : '—'}</td>
                  <td>
                    <span className={`status-pill s-${item.status}`}>
                      {item.status === 'ok' ? 'analyzed' : item.status === 'rejected' ? 'ungradable' : item.status}
                    </span>
                  </td>
                  <td>
                    {item.status === 'ok' && (
                      <button className="btn btn-outline btn-sm" onClick={() => onOpenResult(item.result, item.previewUrl)}>
                        View
                      </button>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}
