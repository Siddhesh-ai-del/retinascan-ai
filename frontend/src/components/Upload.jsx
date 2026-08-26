import React, { useRef, useState } from 'react';
import axios from 'axios';
import { Eye } from 'lucide-react';
import { API_URL, REQUEST_TIMEOUT } from '../config';

/* FastAPI returns `detail` as a string on HTTPException but as an
   array of validation-error objects on 422 — normalize both. */
function extractErrorDetail(err) {
  const detail = err.response?.data?.detail;
  if (!detail) return err.message;
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d) => {
        const loc = Array.isArray(d.loc) ? d.loc.slice(1).join('.') : '';
        return loc ? `${loc}: ${d.msg}` : d.msg;
      })
      .join('; ');
  }
  return String(detail);
}

export default function Upload({ onResult, onAttention, previewUrl, setPreviewUrl, patientId, setPatientId }) {
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [stage, setStage] = useState('idle');
  const [message, setMessage] = useState(null);
  const inputRef = useRef(null);

  const pickFile = (f) => {
    if (!f || !f.type.startsWith('image/')) {
      setMessage({ type: 'error', text: 'Please select a valid image file (JPG/PNG).' });
      return;
    }
    /* Revoke the previous preview URL so repeated picks don't leak blobs. */
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setFile(f);
    setPreviewUrl(URL.createObjectURL(f));
    setMessage(null);
    setStage('idle');
  };

  const onDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    pickFile(e.dataTransfer.files[0]);
  };

  const openPicker = () => {
    if (!busy) inputRef.current.click();
  };

  const analyze = async () => {
    if (!file || busy) return;
    setStage('quality');
    setMessage(null);
    const form = new FormData();
    form.append('file', file);

    try {
      const q = await axios.post(`${API_URL}/api/assess-quality`, form, { timeout: REQUEST_TIMEOUT });
      if (!q.data.gradable) {
        setStage('rejected');
        setMessage({
          type: 'error',
          text: `Image rejected — ${(q.data.quality_issues || []).join(', ')}. ${q.data.feedback || ''}`,
        });
        return;
      }

      setStage('predicting');
      const t0 = performance.now();
      const res = await axios.post(
        `${API_URL}/api/predict?patient_id=${encodeURIComponent(patientId)}`,
        form,
        { timeout: REQUEST_TIMEOUT }
      );
      setStage('done');
      onResult(res.data, Math.round(performance.now() - t0));

      /* Grad-CAM attention is fetched after the main result so it never
         delays screening; failure just means no heatmap layer. */
      if (onAttention) {
        axios
          .post(`${API_URL}/api/explain?patient_id=${encodeURIComponent(patientId)}`, form, { timeout: REQUEST_TIMEOUT })
          .then((a) => onAttention(a.data?.heatmap || null))
          .catch(() => onAttention(null));
      }
    } catch (err) {
      setStage('idle');
      setMessage({ type: 'error', text: `Analysis failed: ${extractErrorDetail(err)}` });
    }
  };

  const busy = stage === 'quality' || stage === 'predicting';

  return (
    <section className="upload-section">
      <div
        className={`dropzone ${dragging ? 'dragging' : ''} ${previewUrl ? 'has-image' : ''}`}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        onClick={openPicker}
        role="button"
        tabIndex={0}
        aria-label="Upload fundus image: click or press Enter to browse, or drag and drop"
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') {
            e.preventDefault();
            openPicker();
          }
        }}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => pickFile(e.target.files[0])}
          aria-label="Fundus image file"
        />
        {previewUrl ? (
          <img src={previewUrl} alt="Fundus preview" className="preview" />
        ) : (
          <div className="dropzone-empty">
            <div className="dz-icon-ring">
              <Eye size={26} strokeWidth={1.5} />
            </div>
            <h2>Drag &amp; drop fundus image</h2>
            <p>or click to browse · JPG / PNG</p>
          </div>
        )}
      </div>

      {busy && (
        <div className="progress-card" role="status" aria-live="polite">
          <div className="spinner" aria-hidden="true" />
          <div>
            <strong>
              {stage === 'quality' ? 'Checking image quality…' : 'Running AI analysis…'}
            </strong>
            <p>{stage === 'quality' ? 'Blur · brightness · glare checks' : 'ICDR classification + lesion segmentation'}</p>
          </div>
        </div>
      )}

      {message && (
        <div
          className={`alert ${message.type === 'error' ? 'alert-error' : 'alert-info'}`}
          role="alert"
        >
          {message.text}
        </div>
      )}

      <div className="upload-controls">
        <label className="field">
          <span>Patient ID</span>
          <input value={patientId} onChange={(e) => setPatientId(e.target.value)} placeholder="PT-0001" />
        </label>
        <button className="btn btn-primary btn-lg" disabled={!file || busy} onClick={analyze}>
          {busy ? 'Analyzing…' : 'Analyze Image'}
        </button>
      </div>

      <p className="hint">
        Tip: use the demo images from <code>/api/demo-images</code> or your own fundus photographs.
      </p>
    </section>
  );
}
