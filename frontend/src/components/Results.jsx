import React from 'react';
import { TriangleAlert, CircleCheck, Zap, Eye } from 'lucide-react';
import LesionOverlay from './LesionOverlay';
import FhirExport from './FhirExport';
import { stageColor as stageColorFor } from '../config';

export default function Results({ result, meta, patientId }) {
  const { classification, segmentation, referral, quality } = result;

  if (result.status === 'rejected') {
    return (
      <section className="results-section">
        <div className="alert alert-error">
          <h3>Image not gradable</h3>
          <p>{quality?.feedback}</p>
          <p className="small">Issues detected: {(quality?.quality_issues || []).join(', ')}</p>
        </div>
      </section>
    );
  }

  /* Guard against malformed success payloads — render the existing error
     style instead of crashing the whole app on a missing field. */
  if (!classification || !referral || !quality) {
    return (
      <section className="results-section">
        <div className="alert alert-error">
          <h3>Incomplete analysis result</h3>
          <p>The server returned an unexpected response. Please try again.</p>
        </div>
      </section>
    );
  }

  const stage = classification.stage;
  const stageColor = stageColorFor(stage);

  return (
    <section className="results-section">
      {result.needs_human_review && (
        <div className="alert alert-warn">
          <h3>
            <Eye size={17} strokeWidth={2} style={{ verticalAlign: '-2px', marginRight: 6 }} />
            Manual review recommended
          </h3>
          <p>
            Model confidence is below the abstention threshold
            {result.review_reasons?.includes('borderline_fundus_quality') ? ' and image quality is borderline' : ''}.
            The stage shown below is a flagged suggestion only — a clinician must confirm before any clinical decision.
          </p>
        </div>
      )}
      {meta?.latencyMs != null && (
        <div className="latency-strip">
          <Zap size={13} strokeWidth={2} />
          Analyzed in {(meta.latencyMs / 1000).toFixed(2)}s · fundus score {quality.fundus_score ?? '—'}
        </div>
      )}
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
                {result.needs_human_review && (
                  <span className="review-pill" style={{ marginLeft: 8 }}>
                    <Eye size={11} strokeWidth={2} /> flagged
                  </span>
                )}
              </div>
            </div>

            <div className="conf-bars">
              {classification.probabilities.map((p, i) => (
                <div key={i} className={`conf-row ${i === stage ? 'active' : ''}`}>
                  <span className="conf-name">{'Stage ' + i}</span>
                  <div className="conf-track">
                    <div
                      className="conf-fill"
                      style={{ width: `${(p * 100).toFixed(1)}%`, background: stageColorFor(i) }}
                    />
                  </div>
                  <span className="conf-val">{(p * 100).toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>

          <div className={`card referral-card ${referral.recommended ? 'urgent' : 'ok'}`}>
            <h3>
              {referral.recommended ? (
                <>
                  <TriangleAlert size={17} strokeWidth={2} /> Referral Recommended
                </>
              ) : (
                <>
                  <CircleCheck size={17} strokeWidth={2} /> No Urgent Referral Needed
                </>
              )}
            </h3>
            <p>
              {referral.overridden_by === 'abstention'
                ? `Deferred to human review: ${referral.urgency}.`
                : referral.recommended
                  ? `Refer to ophthalmologist ${referral.urgency}.`
                  : `Routine follow-up: ${referral.urgency}.`}
            </p>
          </div>

          <FhirExport fhir={result.fhir} patientId={patientId} />
        </div>
      </div>

      <div className="quality-strip">
        <span>Quality: gradable</span>
        <span>Blur score: {quality.blur_score}</span>
        <span>Brightness: {quality.brightness}</span>
        <span>Model confidence: {(classification.confidence * 100).toFixed(1)}%</span>
      </div>
    </section>
  );
}
