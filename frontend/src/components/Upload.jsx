import React, { useRef, useState } from 'react';
import axios from 'axios';

const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

export default function Upload({ onResult, previewUrl, setPreviewUrl, patientId, setPatientId }) {
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

  const analyze = async () => {
    if (!file) return;
    setStage('quality');
    setMessage(null);
    const form = new FormData();
    form.append('file', file);

    try {
      const q = await axios.post(`${API_URL}/api/assess-quality`, form);
      if (!q.data.gradable) {
        setStage('rejected');
        setMessage({
          type: 'error',
          text: `Image rejected — ${q.data.quality_issues.join(', ')}. ${q.data.feedback || ''}`,
        });
        return;
      }

      setStage('predicting');
      const t0 = performance.now();
      const res = await axios.post(`${API_URL}/api/predict?patient_id=${encodeURIComponent(patientId)}`, form);
      setStage('done');
      onResult(res.data, Math.round(performance.now() - t0));
    } catch (err) {
      setStage('idle');
      const detail = err.response?.data?.detail || err.message;
      setMessage({ type: 'error', text: `Analysis failed: ${detail}` });
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
        onClick={() => !busy && inputRef.current.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept="image/*"
          hidden
          onChange={(e) => pickFile(e.target.files[0])}
        />
        {previewUrl ? (
          <img src={previewUrl} alt="Fundus preview" className="preview" />
        ) : (
          <div className="dropzone-empty">
            <div className="dropzone-icon">👁️</div>
            <h2>Drag &amp; drop fundus image</h2>
            <p>or click to browse · JPG / PNG</p>
          </div>
        )}
      </div>

      {busy && (
        <div className="progress-card">
          <div className="spinner" />
          <div>
            <strong>
              {stage === 'quality' ? 'Checking image quality…' : 'Running AI analysis…'}
            </strong>
            <p>{stage === 'quality' ? 'Blur · brightness · glare checks' : 'ICDR classification + lesion segmentation'}</p>
          </div>
        </div>
      )}

      {message && (
        <div className={`alert ${message.type === 'error' ? 'alert-error' : 'alert-info'}`}>
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
