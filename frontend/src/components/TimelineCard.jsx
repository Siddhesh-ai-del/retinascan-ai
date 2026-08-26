import React, { useEffect, useState } from 'react';
import axios from 'axios';
import { History, TrendingDown, TrendingUp, Minus } from 'lucide-react';
import { API_URL, REQUEST_TIMEOUT, stageColor } from '../config';

const EYE_LABELS = { L: 'Left eye', R: 'Right eye', unknown: 'Unspecified eye' };
const TRENDS = {
  improved: { icon: TrendingDown, text: 'improved', color: '#3e8a6c' },
  worsened: { icon: TrendingUp, text: 'worsened', color: '#b04536' },
  stable: { icon: Minus, text: 'stable', color: '#8b867a' },
};

const fmtDate = (ts) => (ts || '').slice(0, 10);

function EyeRow({ eye, data }) {
  const latest = data.latest || {};
  const trend = latest.trend ? TRENDS[latest.trend] : null;
  const TrendIcon = trend?.icon;
  const prev = latest.trend && data.visits.length > 1 ? data.visits[data.visits.length - 2] : null;

  return (
    <div className="timeline-eye">
      <div className="timeline-eye-head">
        <span className="timeline-eye-name">{EYE_LABELS[eye] || eye}</span>
        {latest.stage != null && (
          <span className="stage-chip" style={{ background: stageColor(latest.stage) }}>
            Stage {latest.stage}
          </span>
        )}
        {trend && TrendIcon && (
          <span className="timeline-trend" style={{ color: trend.color }}>
            <TrendIcon size={13} strokeWidth={2} /> {trend.text}
            {prev && prev.stage != null ? ` from Stage ${prev.stage}` : ''}
          </span>
        )}
      </div>
      <p className="small muted">
        {data.count} visit{data.count === 1 ? '' : 's'}
        {latest.ts ? ` · last ${fmtDate(latest.ts)}` : ''}
        {latest.needs_review ? ' · flagged for review' : ''}
      </p>
    </div>
  );
}

export default function TimelineCard({ patientId, refreshKey }) {
  const [timeline, setTimeline] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    if (!patientId) return undefined;
    axios
      .get(`${API_URL}/api/patients/${encodeURIComponent(patientId)}/timeline`, { timeout: REQUEST_TIMEOUT })
      .then((res) => {
        if (!cancelled) {
          setTimeline(res.data);
          setFailed(false);
        }
      })
      .catch(() => {
        if (!cancelled) setFailed(true);
      });
    return () => {
      cancelled = true;
    };
  }, [patientId, refreshKey]);

  if (failed || !timeline || !Object.keys(timeline.eyes || {}).length) return null;
  const total = Object.values(timeline.eyes).reduce((n, e) => n + (e.count || 0), 0);

  return (
    <div className="card timeline-card">
      <h3>
        <History size={16} strokeWidth={2} /> Patient History
      </h3>
      {Object.entries(timeline.eyes).map(([eye, data]) => (
        <EyeRow key={eye} eye={eye} data={data} />
      ))}
      {total <= 1 && <p className="small muted">First recorded visit for this patient ID.</p>}
    </div>
  );
}
