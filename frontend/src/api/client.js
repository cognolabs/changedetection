import axios from 'axios';

const api = axios.create({
  baseURL: '/api',
  timeout: 120000,
});

// ─── Properties ──────────────────────────────────────────────────────────────

export function uploadProperties(file) {
  const form = new FormData();
  form.append('file', file);
  return api.post('/properties/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function listProperties(typology) {
  const params = {};
  if (typology) params.typology = typology;
  return api.get('/properties', { params });
}

export function getPropertiesGeoJSON() {
  return api.get('/properties/geojson');
}

// ─── Videos / Frames ─────────────────────────────────────────────────────────

export function uploadVideo(file) {
  const form = new FormData();
  form.append('file', file);
  return api.post('/videos/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function extractFrames(videoFilename, interval = 1.0) {
  return api.post('/videos/extract-frames', null, {
    params: { video_filename: videoFilename, interval },
  });
}

export function uploadGpx(videoName, file) {
  const form = new FormData();
  form.append('file', file);
  return api.post('/videos/upload-gpx', form, {
    params: { video_name: videoName },
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function listFrames(params = {}) {
  return api.get('/videos/frames', { params });
}

export function getFrameImageUrl(frameId) {
  return `/api/videos/frames/${frameId}/image`;
}

export function geoMatchFrames(bufferMeters = 30) {
  return api.post('/videos/frames/geo-match', null, {
    params: { buffer_meters: bufferMeters },
  });
}

// ─── Inference / Models ──────────────────────────────────────────────────────

export function uploadModel(file) {
  const form = new FormData();
  form.append('file', file);
  return api.post('/inference/upload-model', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
}

export function listModels() {
  return api.get('/inference/models');
}

export function runInference(modelName) {
  return api.post('/inference/run', null, {
    params: { model_name: modelName },
  });
}

export function listPredictions() {
  return api.get('/inference/predictions');
}

// ─── Change Detection ────────────────────────────────────────────────────────

export function detectChanges() {
  return api.post('/changes/detect');
}

export function listChanges(status) {
  const params = {};
  if (status) params.status = status;
  return api.get('/changes', { params });
}

export function getChangesSummary() {
  return api.get('/changes/summary');
}

export function reviewChange(changeId, body) {
  return api.patch(`/changes/${changeId}/review`, body);
}

export function exportChangesCsv() {
  return api.get('/changes/export/csv', { responseType: 'blob' });
}

export function exportChangesGeoJSON() {
  return api.get('/changes/export/geojson', { responseType: 'blob' });
}

// ─── Demo ────────────────────────────────────────────────────────────────────

export function seedDemoData() {
  return api.post('/demo/seed');
}

export function clearAllData() {
  return api.delete('/demo/clear');
}

export default api;
