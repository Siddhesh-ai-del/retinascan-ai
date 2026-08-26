export const API_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';
export const REQUEST_TIMEOUT = 120000;

/* ICDR stage 0-4 — muted earth scale, shared by Results + BatchScreening */
export const STAGE_COLORS = ['#3e8a6c', '#83863c', '#b58424', '#b56128', '#b04536'];

export const stageColor = (stage) => STAGE_COLORS[stage] ?? '#8b867a';
