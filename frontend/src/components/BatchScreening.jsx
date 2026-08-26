import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Layers, TriangleAlert, Eye } from 'lucide-react';
import { API_URL, REQUEST_TIMEOUT, stageColor } from '../config';

export default function BatchScreening({ onOpenResult }) {
  const [queue, setQueue] = useState([]);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(0);
  const createdUrls = useRef([]);
  const handedOffUrl = useRef(null);

  /* Revoke every blob URL this component created — except one that was
     handed off to App (View button) and is still rendering elsewhere. */
  const revokeCreated = () => {
    createdUrls.current.forEach((u) => {
      if (u && u !== handedOffUrl.current) URL.revokeObjectURL(u);
    });
    createdUrls.current = [];
  };

  useEffect(() => revokeCreated, []);

  const runAll = async (files) => {
    revokeCreated();
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
        const res = await axios.post(
          `${API_URL}/api/predict?patient_id=batch`,
          form,
          { timeout: REQUEST_TIMEOUT }
        );
        items[i].result = res.data;
        items[i].status = res.data.status === 'rejected' ? 'rejected' : 'ok';
      } catch (err) {
        items[i].status = 'error';
        items[i].result = null;
      }
      const url = URL.createObjectURL(items[i].file);
      items[i].previewUrl = url;
      createdUrls.current.push(url);
      setQueue([...items]);
      setDone(i + 1);
    }
    setRunning(false);
  };

  const openResult = (result, url) => {
    handedOffUrl.current = url || null;
    onOpenResult(result, url);
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
          onChange={(e) => {
            if (e.target.files.length) runAll(e.target.files);
            /* Reset so re-selecting the same files re-fires onChange. */
            e.target.value = '';
          }}
          aria-label="Select multiple fundus images"
        />
        <div className="dropzone-empty">
          <div className="dz-icon-ring">
            <Layers size={24} strokeWidth={1.5} />
          </div>
          <h2>{running ? `Screening ${done}/${queue.length}…` : 'Select multiple fundus images'}</h2>
          <p>batch screening · sorted by severity</p>
        </div>
      </label>

      {running && (
        <div className="batch-progress-track">
          <div className="batch-progress-fill" style={{ width: `${(done / Math.max(queue.length, 1)) * 100}%` }} />
        </div>
      )}

      {queue.some((q) => q.status !== 'queued' && q.status !== 'running') && (
        <table className="batch-table card">
          <thead>
            <tr>
              <th></th>
              <th>Patient image</th>
              <th>ICDR stage</th>
              <th>Confidence</th>
              <th>Review</th>
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
                <tr key={`${item.name}-${item.previewUrl}`}>
                  <td>
                    {item.previewUrl && (
                      <img src={item.previewUrl} alt={`Fundus: ${item.name}`} className="row-thumb" />
                    )}
                  </td>
                  <td className="row-name">{item.name}</td>
                  <td>
                    {c ? (
                      <span className="stage-chip" style={{ background: stageColor(c.stage) }}>
                        {c.stage} · {c.label}
                      </span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>{c ? `${(c.confidence * 100).toFixed(0)}%` : '—'}</td>
                  <td>
                    {item.result?.needs_human_review ? (
                      <span className="review-pill">
                        <Eye size={12} strokeWidth={2} /> review
                      </span>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td className="small">
                    {ref ? (
                      ref.recommended ? (
                        <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, color: 'var(--danger-deep)' }}>
                          <TriangleAlert size={13} strokeWidth={2} /> {ref.urgency}
                        </span>
                      ) : (
                        'routine'
                      )
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>
                    <span className={`status-pill s-${item.status}`}>
                      {item.status === 'ok' ? 'analyzed' : item.status === 'rejected' ? 'ungradable' : item.status}
                    </span>
                  </td>
                  <td>
                    {item.status === 'ok' && (
                      <button className="btn btn-outline btn-sm" onClick={() => openResult(item.result, item.previewUrl)}>
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
