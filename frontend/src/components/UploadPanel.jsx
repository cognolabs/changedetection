import React, { useState, useEffect, useRef } from 'react';
import {
  uploadProperties,
  uploadVideo,
  extractFrames,
  uploadGpx,
  uploadModel,
  listModels,
  geoMatchFrames,
  runInference,
  detectChanges,
  seedDemoData,
  clearAllData,
} from '../api/client';

function FileUploadRow({ label, accept, onUpload, hint }) {
  const inputRef = useRef(null);
  const [loading, setLoading] = useState(false);
  const [feedback, setFeedback] = useState(null);

  async function handleFileChange(e) {
    const selected = e.target.files?.[0];
    if (!selected) return;
    setLoading(true);
    setFeedback(null);
    try {
      await onUpload(selected);
      setFeedback({ type: 'success', message: `${selected.name} uploaded.` });
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        'Upload failed.';
      setFeedback({ type: 'error', message: msg });
    } finally {
      setLoading(false);
      if (inputRef.current) inputRef.current.value = '';
    }
  }

  return (
    <div className="upload-row">
      <label className="upload-label">{label}</label>
      {hint && <p className="upload-hint">{hint}</p>}
      <div className="upload-controls">
        <input
          ref={inputRef}
          type="file"
          accept={accept}
          className="file-input"
          disabled={loading}
          onChange={handleFileChange}
        />
        {loading && (
          <span className="btn-loading">
            <span className="spinner" />
            Uploading...
          </span>
        )}
      </div>
      {feedback && (
        <div className={`feedback feedback-${feedback.type} feedback-sm`}>
          {feedback.type === 'success' ? (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6 9 17l-5-5"/></svg>
          ) : (
            <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/></svg>
          )}
          {feedback.message}
        </div>
      )}
    </div>
  );
}

export default function UploadPanel({ onRefresh }) {
  const [videoFilename, setVideoFilename] = useState('');
  const [gpxVideoName, setGpxVideoName] = useState('');
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [actionLoading, setActionLoading] = useState('');
  const [actionFeedback, setActionFeedback] = useState({});

  useEffect(() => {
    loadModels();
  }, []);

  function loadModels() {
    listModels()
      .then((r) => {
        const list = Array.isArray(r.data) ? r.data : [];
        setModels(list);
        if (list.length > 0 && !selectedModel) {
          setSelectedModel(
            typeof list[0] === 'string' ? list[0] : list[0].name || list[0].model_name || ''
          );
        }
      })
      .catch(() => {});
  }

  async function runAction(key, fn) {
    setActionLoading(key);
    setActionFeedback((prev) => ({ ...prev, [key]: null }));
    try {
      const res = await fn();
      const msg =
        res.data?.message || res.data?.detail || `${key} completed successfully.`;
      setActionFeedback((prev) => ({
        ...prev,
        [key]: { type: 'success', message: msg },
      }));
      if (onRefresh) onRefresh();
    } catch (err) {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.message ||
        `${key} failed.`;
      setActionFeedback((prev) => ({
        ...prev,
        [key]: { type: 'error', message: msg },
      }));
    } finally {
      setActionLoading('');
    }
  }

  function ActionFeedback({ actionKey }) {
    const fb = actionFeedback[actionKey];
    if (!fb) return null;
    return (
      <div className={`feedback feedback-${fb.type} feedback-sm`}>
        {fb.type === 'success' ? (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M20 6 9 17l-5-5"/></svg>
        ) : (
          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><circle cx="12" cy="12" r="10"/><path d="m15 9-6 6M9 9l6 6"/></svg>
        )}
        {fb.message}
      </div>
    );
  }

  return (
    <div className="upload-panel">
      {/* Demo Data / Clear */}
      <div className="upload-section demo-section">
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <button
            className="btn btn-demo"
            disabled={!!actionLoading}
            onClick={() => runAction('demo', () => seedDemoData())}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 12a9 9 0 1 1-6.219-8.56"/><polyline points="21 3 21 9 15 9"/></svg>
            {actionLoading === 'demo' ? 'Loading Demo...' : 'Load Demo Data'}
          </button>
          <button
            className="btn btn-danger"
            disabled={!!actionLoading}
            onClick={() => {
              if (window.confirm('Clear ALL data? This cannot be undone.')) {
                runAction('clear', () => clearAllData());
              }
            }}
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            {actionLoading === 'clear' ? 'Clearing...' : 'Clear All Data'}
          </button>
        </div>
        <span className="demo-hint">Prayagraj Civil Lines sample dataset</span>
        <ActionFeedback actionKey="demo" />
        <ActionFeedback actionKey="clear" />
      </div>

      <div className="section-divider" />

      {/* Step 1: Property Data */}
      <div className="upload-section">
        <div className="step-header">
          <span className="step-number">1</span>
          <div>
            <h3 className="upload-section-title">Property Data</h3>
            <p className="step-desc">Upload ward shapefiles or KML</p>
          </div>
        </div>

        <div className="shapefile-guide">
          <div className="guide-label">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/></svg>
            ZIP your ward folder containing:
          </div>
          <div className="guide-items">
            <span className="guide-chip guide-polygon">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><path d="M3 3h18v18H3z" opacity="0.3"/><path d="M3 3h18v18H3V3z" fill="none" stroke="currentColor" strokeWidth="2"/></svg>
              Plot Shapefiles (polygons)
            </span>
            <span className="guide-chip guide-point">
              <svg width="10" height="10" viewBox="0 0 24 24" fill="currentColor"><circle cx="12" cy="12" r="5"/></svg>
              Survey Data (points)
            </span>
          </div>
          <p className="guide-note">Joined automatically by Parcel ID</p>
        </div>

        <FileUploadRow
          label="Shapefile ZIP or KML/KMZ"
          accept=".zip,.kml,.kmz"
          onUpload={(file) => uploadProperties(file).then((r) => { onRefresh(); return r; })}
        />
      </div>

      {/* Step 2: Video & Frames */}
      <div className="upload-section">
        <div className="step-header">
          <span className="step-number">2</span>
          <div>
            <h3 className="upload-section-title">Video & Frames</h3>
            <p className="step-desc">Survey video footage + GPS track</p>
          </div>
        </div>

        <FileUploadRow
          label="Video file"
          accept="video/*,.mp4,.avi,.mov,.mkv"
          onUpload={(file) =>
            uploadVideo(file).then((r) => {
              const fname = r.data?.detail?.file || r.data?.filename || file.name;
              setVideoFilename(fname);
              setGpxVideoName(fname.replace(/\.[^.]+$/, ''));
              onRefresh();
              return r;
            })
          }
        />

        {videoFilename && (
          <div className="upload-row">
            <label className="upload-label">
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></svg>
              Extract frames from: <strong>{videoFilename}</strong>
            </label>
            <button
              className="btn btn-action btn-sm"
              disabled={actionLoading === 'extract'}
              onClick={() =>
                runAction('extract', () => extractFrames(videoFilename))
              }
            >
              {actionLoading === 'extract' ? (
                <span className="btn-loading"><span className="spinner" />Extracting...</span>
              ) : 'Extract Frames'}
            </button>
            <ActionFeedback actionKey="extract" />
          </div>
        )}

        <FileUploadRow
          label="GPS track (GPX / KML / KMZ)"
          accept=".gpx,.kml,.kmz"
          onUpload={(file) => {
            const vname = gpxVideoName || videoFilename?.replace(/\.[^.]+$/, '') || '';
            return uploadGpx(vname, file).then((r) => { onRefresh(); return r; });
          }}
        />
      </div>

      {/* Step 3: Model */}
      <div className="upload-section">
        <div className="step-header">
          <span className="step-number">3</span>
          <div>
            <h3 className="upload-section-title">Inference Model</h3>
            <p className="step-desc">YOLO classification model</p>
          </div>
        </div>
        <FileUploadRow
          label="YOLO model (.pt)"
          accept=".pt"
          onUpload={(file) =>
            uploadModel(file).then((r) => {
              loadModels();
              return r;
            })
          }
        />
      </div>

      {/* Step 4: Pipeline */}
      <div className="upload-section">
        <div className="step-header">
          <span className="step-number">4</span>
          <div>
            <h3 className="upload-section-title">Run Pipeline</h3>
            <p className="step-desc">Process and detect changes</p>
          </div>
        </div>

        <div className="pipeline-actions">
          <div className="action-row">
            <button
              className="btn btn-action"
              disabled={!!actionLoading}
              onClick={() => runAction('geo-match', () => geoMatchFrames(30))}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
              {actionLoading === 'geo-match' ? 'Matching...' : 'Geo-Match Frames'}
            </button>
            <ActionFeedback actionKey="geo-match" />
          </div>

          <div className="action-row">
            <div className="action-row-inline">
              <select
                className="input select"
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
              >
                {models.length === 0 && <option value="">No models</option>}
                {models.map((m, i) => {
                  const name = typeof m === 'string' ? m : m.name || m.model_name || `Model ${i}`;
                  return (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  );
                })}
              </select>
              <button
                className="btn btn-action"
                disabled={!!actionLoading || !selectedModel}
                onClick={() =>
                  runAction('inference', () => runInference(selectedModel))
                }
              >
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
                {actionLoading === 'inference' ? 'Running...' : 'Inference'}
              </button>
            </div>
            <ActionFeedback actionKey="inference" />
          </div>

          <div className="action-row">
            <button
              className="btn btn-detect"
              disabled={!!actionLoading}
              onClick={() => runAction('detect', () => detectChanges())}
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="9" y1="15" x2="15" y2="15"/></svg>
              {actionLoading === 'detect' ? 'Detecting...' : 'Detect Changes'}
            </button>
            <ActionFeedback actionKey="detect" />
          </div>
        </div>
      </div>
    </div>
  );
}
