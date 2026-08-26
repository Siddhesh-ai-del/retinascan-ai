import React, { useState } from 'react';
import { Code2, Copy, Check, Download } from 'lucide-react';

export default function FhirExport({ fhir, patientId }) {
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState(false);

  if (!fhir) return null;
  const json = JSON.stringify(fhir, null, 2);

  const copy = async () => {
    /* navigator.clipboard only exists in secure contexts (https/localhost).
       Fall back to a temporary textarea for LAN-IP demos. */
    if (navigator.clipboard?.writeText) {
      try {
        await navigator.clipboard.writeText(json);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
        return;
      } catch {
        /* fall through to legacy path */
      }
    }
    try {
      const ta = document.createElement('textarea');
      ta.value = json;
      ta.setAttribute('readonly', '');
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      const ok = document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(ok);
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
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    /* Defer revocation — revoking synchronously after click() can abort
       the download in Firefox. */
    setTimeout(() => URL.revokeObjectURL(url), 1000);
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
            <Code2 size={13} strokeWidth={2} />
            {open ? 'Hide JSON' : 'View JSON'}
          </button>
          <button className="btn btn-outline btn-sm" onClick={copy}>
            {copied ? <Check size={13} strokeWidth={2.5} /> : <Copy size={13} strokeWidth={2} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
          <button className="btn btn-primary btn-sm" onClick={download}>
            <Download size={13} strokeWidth={2} />
            Download .json
          </button>
        </div>
      </div>
      {open && <pre className="fhir-json">{json}</pre>}
    </div>
  );
}
