import React, { useState } from 'react';
import LesionOverlay from './LesionOverlay';
import FhirExport from './FhirExport';

const STAGE_COLORS = ['#2ecc71', '#a3e635', '#f59e0b', '#f97316', '#ef4444'];

export default function Results({ result, patientId }) {
  const { classification, segmentation, referral, quality } = result;

  if (result.status === 'rejected') {
    return (
      <section className="results-section">
        <div className="alert alert-error">
          <h3>Image not gradable</h3>
          <p>{quality.feedback}</p>
          <p className="small">Issues detected: {quality.quality_issues.join(', ')}</p>
        </div>
      </section>
    );
  }

  const stage = classification.stage;
  const stageColor = STAGE_COLORS[stage];

  return (
    <section className="results-section">
      <div className="results-grid">
        <div className="card overlay-card">
          <LesionOverlay segmentation={segmentation} />
        </div>

        <div className="stack">
          <div className="card grade-card" style={{ borderLeftColor: stageColor }}>
            <div className="grade-head">
              <div>
                <span className="grade-label">ICDR Severity</span>
                <h2 style={{ color: stageColor }}>{classification.label}</h2>
              </div>
              <div className="grade-badge" style={{ background: stageColor }}>
                Stage {stage}
              </div>
            </div>

            <div className="conf-bars">
              {classification.probabilities.map((p, i) => (
                <div key={i} className={`conf-row ${i === stage ? 'active' : ''}`}>
                  <span className="conf-name">{'Stage ' + i}</span>
                  <div className="conf-track">
                    <div
                      className="conf-fill"
                      style={{ width: `${(p * 100).toFixed(1)}%`, background: STAGE_COLORS[i] }}
                    />
                  </div>
                  <span className="conf-val">{(p * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>

          <div className={`card referral-card ${referral.recommended ? 'urgent' : 'ok'}`}>
            <h3>{referral.recommended ? '⚠ Referral Recommended' : '✓ No Urgent Referral Needed'}</h3>
            <p>
              {referral.recommended
                ? `Refer to ophthalmologist ${referral.urgency}.`
                : `Routine follow-up: ${referral.urgency}.`}
            </p>
          </div>

          <FhirExport fhir={result.fhir} patientId={patientId} />
        </div>
      </div>

      <div className="quality-strip">
        <span>Quality: gradable ✓</span>
        <span>Blur score: {quality.blur_score}</span>
        <span>Brightness: {quality.brightness}</span>
        <span>Model confidence: {(classification.confidence * 100).toFixed(1)}%</span>
      </div>
    </section>
  );
}
