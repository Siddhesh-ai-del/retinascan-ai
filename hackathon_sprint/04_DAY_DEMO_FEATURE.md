# Day 6: Killer Demo Feature — Batch Triage View

## Deadline
- **Day 6 full day:** Build and polish the batch triage feature
- **STOP when:** Upload 10+ images → sorted table with urgency → export works

## Goal
Build the feature that makes judges say "wow" — upload a batch of images and see them automatically triaged by severity in seconds.

## Why Batch Triage
- Shows the **system** working at scale, not just one image
- Demonstrates real clinical workflow (screening camp scenario)
- The existing `BatchScreening.jsx` component already exists — we polish it

---

## Task 1: Backend — Batch Endpoint (2 hours)

### Create: `src/api/server.py` — add batch endpoint

Add after the existing endpoints:

```python
@app.post("/api/batch-predict")
async def batch_predict(
    request: Request,
    files: list[UploadFile] = File(...),
    patient_id: str = "batch",
):
    """Process multiple images in one request."""
    _check_auth(request)
    _check_rate_limit(request)
    if predictor is None or not predictor.is_ready():
        raise HTTPException(status_code=503, detail="Models not loaded yet.")

    results = []
    for file in files[:20]:  # Cap at 20 images
        _validate_upload(file)
        path = await _save_and_keep(file)
        try:
            result = await anyio.to_thread.run_sync(predictor.predict, path, patient_id)
            result["filename"] = file.filename
            results.append(result)
        except Exception as e:
            logger.exception("Batch prediction failed for %s", file.filename)
            results.append({
                "filename": file.filename,
                "status": "error",
                "error": str(e),
            })
        finally:
            path.unlink(missing_ok=True)

    # Sort by severity (most severe first)
    def sort_key(r):
        if r.get("status") != "ok" or not r.get("classification"):
            return -1  # rejected/error at top
        return r["classification"]["stage"]

    results.sort(key=sort_key, reverse=True)

    summary = {
        "total": len(results),
        "screened": sum(1 for r in results if r.get("status") == "ok"),
        "rejected": sum(1 for r in results if r.get("status") == "rejected"),
        "errors": sum(1 for r in results if r.get("status") == "error"),
        "urgent": sum(1 for r in results if r.get("referral", {}).get("recommended", False)),
        "needs_review": sum(1 for r in results if r.get("needs_human_review", False)),
    }

    return {"summary": summary, "results": results}
```

### Test
```bash
# Restart backend
pkill -f "uvicorn src.api.server"; sleep 1
cd /home/siddhesh/Desktop/Draft_confidential
venv/bin/python -m uvicorn src.api.server:app --host 127.0.0.1 --port 8000 &

# Test with demo images
curl -X POST http://localhost:8000/api/batch-predict \
  -F "files=@demo_images/healthy.jpg" \
  -F "files=@demo_images/moderate_npdr.jpg" | python -m json.tool
```

---

## Task 2: Frontend — Enhanced BatchView (3 hours)

### Rewrite: `frontend/src/components/BatchScreening.jsx`

Key improvements:
1. Progress bar with per-image status
2. Summary cards (total/urgent/review/rejected)
3. Sortable table with severity coloring
4. Export to CSV button
5. "View" button to see individual results

```jsx
import React, { useEffect, useRef, useState } from 'react';
import axios from 'axios';
import { Layers, TriangleAlert, Eye, Download, CheckCircle, XCircle } from 'lucide-react';
import { API_URL, REQUEST_TIMEOUT, stageColor } from '../config';

export default function BatchScreening({ onOpenResult }) {
  const [queue, setQueue] = useState([]);
  const [running, setRunning] = useState(false);
  const [done, setDone] = useState(0);
  const [summary, setSummary] = useState(null);
  const createdUrls = useRef([]);
  const handedOffUrl = useRef(null);

  const revokeCreated = () => {
    createdUrls.current.forEach((u) => {
      if (u && u !== handedOffUrl.current) URL.revokeObjectURL(u);
    });
    createdUrls.current = [];
  };
  useEffect(() => revokeCreated, []);

  const runAll = async (files) => {
    revokeCreated();
    setSummary(null);
    const items = Array.from(files).map((f) => ({
      file: f, name: f.name, status: 'queued', result: null,
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
      } catch {
        items[i].status = 'error';
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

  const openResult = (result, url) => {
    handedOffUrl.current = url || null;
    onOpenResult(result, url);
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

  const sorted = [...queue].sort((a, b) => {
    const sa = a.result?.classification?.stage ?? -1;
    const sb = b.result?.classification?.stage ?? -1;
    return sb - sa;
  });

  return (
    <div className="batch-section">
      <label className="dropzone batch-drop">
        <input
          type="file" accept="image/*" multiple hidden disabled={running}
          onChange={(e) => {
            if (e.target.files.length) runAll(e.target.files);
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
              <div className="small-muted">Rejected</div>
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
                    <td>{item.previewUrl && <img src={item.previewUrl} alt="" className="row-thumb" />}</td>
                    <td className="row-name">{item.name}</td>
                    <td>
                      {c ? (
                        <span className="stage-chip" style={{ background: stageColor(c.stage) }}>
                          {c.stage} · {c.label}
                        </span>
                      ) : <span className="muted">—</span>}
                    </td>
                    <td>{c ? `${(c.confidence * 100).toFixed(0)}%` : '—'}</td>
                    <td>
                      {item.result?.needs_human_review ? (
                        <span className="review-pill"><Eye size={12} /> review</span>
                      ) : <span className="muted">—</span>}
                    </td>
                    <td className="small">
                      {ref?.recommended ? (
                        <span style={{ color: 'var(--danger-deep)' }}>
                          <TriangleAlert size={13} /> {ref.urgency}
                        </span>
                      ) : 'routine'}
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
```

---

## Task 3: Prepare Demo Images (30 minutes)

### Create diverse test images

```bash
# Verify demo images exist
ls demo_images/
# Should have: healthy.jpg, moderate_npdr.jpg, blurry_ungradable.jpg
# Need to add: mild_npdr.jpg, severe_npdr.jpg, proliferative_dr.jpg
```

If missing images, extract from training data:
```python
# Quick script to extract one sample per stage from APTOS
import pandas as pd
import shutil
from pathlib import Path

df = pd.read_csv("data/raw/aptos/train.csv")
img_dir = Path("data/raw/aptos/train_images")
out_dir = Path("demo_images")

for stage in range(5):
    sample = df[df["diagnosis"] == stage].iloc[0]
    src = img_dir / f"{sample['id_code']}.png"
    names = {0: "healthy", 1: "mild_npdr", 2: "moderate_npdr", 3: "severe_npdr", 4: "proliferative_dr"}
    dst = out_dir / f"{names[stage]}.jpg"
    if not dst.exists() and src.exists():
        shutil.copy2(src, dst)
        print(f"Copied {src.name} -> {dst.name}")
```

### Test All 5 Stages
Upload each image individually and verify:
- [ ] healthy.jpg → Stage 0, "No DR", no referral
- [ ] mild_npdr.jpg → Stage 1, "Mild NPDR", routine
- [ ] moderate_npdr.jpg → Stage 2, "Moderate NPDR", refer within 4 weeks
- [ ] severe_npdr.jpg → Stage 3, "Severe NPDR", refer within 2 weeks
- [ ] proliferative_dr.jpg → Stage 4, "Proliferative DR", immediate referral

---

## Task 4: End-to-End Demo Test (1 hour)

### Full Flow Test
1. `bash start_demo.sh`
2. Open http://localhost:3000
3. Single image: Upload moderate_npdr.jpg → see results → check overlays → download PDF
4. Batch mode: Select all 5 demo images → see sorted table → export CSV
5. Check FHIR JSON → validate structure
6. Check patient timeline → shows history

### Timing Test
```bash
# Time a single prediction
time curl -s -X POST http://localhost:8000/api/predict \
  -F "file=@demo_images/moderate_npdr.jpg" \
  -F "patient_id=test" | python -c "import sys,json; d=json.load(sys.stdin); print(f'Status: {d[\"status\"]}, Stage: {d.get(\"classification\",{}).get(\"stage\",\"N/A\")}')"
# Target: < 3 seconds total
```

---

## Go/No-Go Criteria

| Check | Status |
|---|---|
| Batch upload works (10+ images) | Required |
| Results sorted by severity | Required |
| Summary cards show correct counts | Required |
| CSV export works | Required |
| "View" button shows individual result | Required |
| All 5 demo images produce correct stages | Required |
| PDF report downloads | Required |
| FHIR JSON valid | Required |
| No console errors | Required |
| Total demo flow < 30 seconds | Nice to have |
