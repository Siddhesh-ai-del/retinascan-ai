import json
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS visits (
  id TEXT PRIMARY KEY,
  patient_id TEXT NOT NULL,
  eye TEXT NOT NULL DEFAULT 'unknown' CHECK (eye IN ('L','R','unknown')),
  ts TEXT NOT NULL,
  stage INTEGER,
  confidence REAL,
  needs_review INTEGER NOT NULL DEFAULT 0,
  fhir_json TEXT
);
CREATE INDEX IF NOT EXISTS idx_visits_patient ON visits(patient_id, eye, ts);
"""

VALID_EYES = ("L", "R", "unknown")


class VisitStore:
    """Tiny sqlite-backed visit history (stdlib sqlite3, WAL, thread-safe)."""

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        conn = sqlite3.connect(self.db_path)
        try:
            conn.executescript(SCHEMA)
            conn.commit()
        finally:
            conn.close()

    def _connect(self):
        conn = sqlite3.connect(self.db_path, timeout=10)
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def add_visit(self, patient_id, eye, stage, confidence, needs_review, fhir_json):
        visit_id = uuid.uuid4().hex[:16]
        ts = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock:
            conn = self._connect()
            try:
                conn.execute(
                    "INSERT INTO visits (id, patient_id, eye, ts, stage, confidence, needs_review, fhir_json) VALUES (?,?,?,?,?,?,?,?)",
                    (visit_id, patient_id, eye, ts, stage, confidence, int(bool(needs_review)), fhir_json),
                )
                conn.commit()
            finally:
                conn.close()
        return {"id": visit_id, "ts": ts, "eye": eye}

    def timeline(self, patient_id):
        with self._lock:
            conn = self._connect()
            try:
                rows = conn.execute(
                    "SELECT id, eye, ts, stage, confidence, needs_review FROM visits "
                    "WHERE patient_id = ? ORDER BY ts ASC",
                    (patient_id,),
                ).fetchall()
            finally:
                conn.close()

        by_eye = {"L": [], "R": [], "unknown": []}
        prev_stage = {}
        for visit_id, eye, ts, stage, confidence, needs_review in rows:
            prev = prev_stage.get(eye)
            if prev is None or stage is None:
                trend = None
            else:
                trend = "improved" if stage < prev else ("worsened" if stage > prev else "stable")
            prev_stage[eye] = stage if stage is not None else prev
            by_eye.setdefault(eye, []).append(
                {
                    "id": visit_id,
                    "ts": ts,
                    "stage": stage,
                    "confidence": confidence,
                    "needs_review": bool(needs_review),
                    "trend": trend,
                }
            )

        eyes_out = {}
        for eye, visits in by_eye.items():
            if not visits:
                continue
            eyes_out[eye] = {"visits": visits, "latest": visits[-1], "count": len(visits)}
        return {"patient_id": patient_id, "eyes": eyes_out}


def fhir_to_json(fhir) -> str:
    try:
        return json.dumps(fhir)
    except (TypeError, ValueError):
        return None
