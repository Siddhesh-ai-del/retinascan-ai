import React, { useState } from 'react';

export default function FhirExport({ fhir, patientId }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!fhir) return null;
  const json = JSON.stringify(fhir, null, 2);

  const copy = async () => {
    try {
      await navigator.clipboard.writeText(json);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      setCopied(false);
    }
  };

  const download = () => {
    const blob = new Blob([json], { type: 'application/fhir+json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `DiagnosticReport_${patientId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="card fhir-card">
      <div className="fhir-head">
        <div>
          <h3>HL7 FHIR R4 Report</h3>
          <p className="small muted">DiagnosticReport · Patient/{patientId}</p>
        </div>
        <div className="fhir-actions">
          <button className="btn btn-outline btn-sm" onClick={() => setOpen(!open)}>
            {open ? 'Hide JSON' : 'View JSON'}
          </button>
          <button className="btn btn-outline btn-sm" onClick={copy}>
            {copied ? 'Copied ✓' : 'Copy'}
          </button>
          <button className="btn btn-primary btn-sm" onClick={download}>
            Download .json
          </button>
        </div>
      </div>
      {open && <pre className="fhir-json">{json}</pre>}
    </div>
  );
}
