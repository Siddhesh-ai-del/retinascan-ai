import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Layers, TriangleAlert, Eye, Download } from 'lucide-react';
import { API_URL, REQUEST_TIMEOUT, stageColor } from '../config';

export default function BatchScreening({ onOpenResult }) {
  const [queue, setQueue] = useState([]);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(0);
  const [summary, setSummary] = useState(null);
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

    // Compute summary
    const screened = items.filter((x) => x.status === 'ok').length;
    const rejected = items.filter((x) => x.status === 'rejected').length;
    const urgent = items.filter((x) => x.result?.referral?.recommended).length;
    const review = items.filter((x) => x.result?.needs_human_review).length;
    setSummary({ total: items.length, screened, rejected, urgent, review });
  };

  const exportCSV = () => {
    const header = 'Filename,Stage,Label,Confidence,Referral,Review,Status\n';
    const rows = queue
      .filter((q) => q.status !== 'queued' && q.status !== 'running')
      .map((q) => {
        const c = q.result?.classification;
        const r = q.result?.referral;
        return [
          q.name,
          c?.stage ?? '',
          c?.label ?? '',
          c ? (c.confidence * 100).toFixed(1) + '%' : '',
          r?.recommended ? r.urgency : 'routine',
          q.result?.needs_human_review ? 'yes' : 'no',
          q.status,
        ].join(',');
      })
      .join('\n');
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'screening_results.csv';
    a.click();
    URL.revokeObjectURL(url);
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

      {/* Summary Cards */}
      {summary && (
        <div className="batch-summary" style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
          <div className="card" style={{ flex: 1, minWidth: 120, textAlign: 'center', padding: 16 }}>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{summary.total}</div>
            <div className="small muted">Total</div>
          </div>
          <div className="card" style={{ flex: 1, minWidth: 120, textAlign: 'center', padding: 16, borderLeft: '3px solid var(--ok)' }}>
            <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--ok-deep)' }}>{summary.screened}</div>
            <div className="small muted">Screened</div>
          </div>
          {summary.urgent > 0 && (
            <div className="card" style={{ flex: 1, minWidth: 120, textAlign: 'center', padding: 16, borderLeft: '3px solid var(--danger)' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--danger-deep)' }}>{summary.urgent}</div>
              <div className="small muted">Urgent Referral</div>
            </div>
          )}
          {summary.review > 0 && (
            <div className="card" style={{ flex: 1, minWidth: 120, textAlign: 'center', padding: 16, borderLeft: '3px solid var(--warn)' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--warn-deep)' }}>{summary.review}</div>
              <div className="small muted">Needs Review</div>
            </div>
          )}
          {summary.rejected > 0 && (
            <div className="card" style={{ flex: 1, minWidth: 120, textAlign: 'center', padding: 16, borderLeft: '3px solid var(--muted)' }}>
              <div style={{ fontSize: 28, fontWeight: 700, color: 'var(--muted)' }}>{summary.rejected}</div>
              <div className="small muted">Rejected</div>
            </div>
          )}
        </div>
      )}

      {/* Results Table */}
      {queue.some((q) => q.status !== 'queued' && q.status !== 'running') && (
        <>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
            <h3 style={{ margin: 0 }}>Results ({queue.length} images)</h3>
            <button className="btn btn-outline btn-sm" onClick={exportCSV}>
              <Download size={13} strokeWidth={2} /> Export CSV
            </button>
          </div>
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
        </>
      )}
    </div>
  );
}
