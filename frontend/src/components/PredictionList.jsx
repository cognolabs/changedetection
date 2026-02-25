import React, { useState } from 'react';
import { getPredictionImageUrl } from '../api/client';

export default function PredictionList({ predictions, frames, onSelectProperty }) {
  const [filterClass, setFilterClass] = useState('all');
  const [expandedId, setExpandedId] = useState(null);
  const [modalImg, setModalImg] = useState(null);

  // Build frame lookup
  const frameById = {};
  (frames || []).forEach((f) => { frameById[f.id] = f; });

  // Get unique predicted classes
  const classes = [...new Set(predictions.map((p) => p.predicted_class))].sort();

  const filtered =
    filterClass === 'all'
      ? predictions
      : predictions.filter((p) => p.predicted_class === filterClass);

  // Sort by confidence descending
  const sorted = [...filtered].sort(
    (a, b) => (b.confidence || 0) - (a.confidence || 0)
  );

  function handleRowClick(pred) {
    setExpandedId(expandedId === pred.id ? null : pred.id);
  }

  function handleGoToProperty(propId) {
    if (propId && onSelectProperty) onSelectProperty(propId);
  }

  return (
    <div className="change-list">
      {/* Filter Bar */}
      <div className="change-list-header">
        <div className="filter-group">
          <button
            className={`filter-btn ${filterClass === 'all' ? 'active' : ''}`}
            onClick={() => setFilterClass('all')}
          >
            All
          </button>
          {classes.map((cls) => (
            <button
              key={cls}
              className={`filter-btn ${filterClass === cls ? 'active' : ''}`}
              onClick={() => setFilterClass(cls)}
            >
              {cls}
              <span className="filter-count">
                {predictions.filter((p) => p.predicted_class === cls).length}
              </span>
            </button>
          ))}
        </div>
      </div>

      {/* List */}
      {sorted.length === 0 ? (
        <div className="empty-state-small">
          <p>No predictions yet.</p>
          <p className="hint">
            Upload frames, run inference to generate predictions.
          </p>
        </div>
      ) : (
        <div className="pred-list-wrapper">
          {sorted.map((pred) => {
            const frame = frameById[pred.frame_id];
            const propId = frame?.matched_property_id;
            const isExpanded = expandedId === pred.id;

            return (
              <div key={pred.id} className={`pred-card ${isExpanded ? 'pred-card-expanded' : ''}`}>
                <div className="pred-card-header" onClick={() => handleRowClick(pred)}>
                  <div className="pred-card-left">
                    <span className="pred-frame-id">Frame #{pred.frame_id}</span>
                    {propId && <span className="pred-prop-id">Property #{propId}</span>}
                  </div>
                  <div className="pred-card-right">
                    <span className={`status-badge status-${pred.predicted_class === 'commercial' ? 'flagged' : 'approved'}`}>
                      {pred.predicted_class}
                    </span>
                    <span className="pred-conf-badge">
                      {pred.confidence != null ? `${(pred.confidence * 100).toFixed(0)}%` : '-'}
                    </span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="pred-card-body">
                    <div
                      className="pred-frame-preview"
                      style={{ cursor: 'pointer' }}
                      onClick={(e) => {
                        e.stopPropagation();
                        setModalImg({ src: getPredictionImageUrl(pred.id), label: `Frame #${pred.frame_id}`, pred });
                      }}
                    >
                      <img
                        src={getPredictionImageUrl(pred.id)}
                        alt={`Prediction ${pred.id}`}
                        className="pred-frame-img"
                        onError={(e) => { e.target.style.display = 'none'; }}
                      />
                    </div>
                    <div className="pred-detail-grid">
                      <div className="pred-detail-item">
                        <span className="pred-detail-label">Model</span>
                        <span className="pred-detail-value">{pred.model_name || '-'}</span>
                      </div>
                      <div className="pred-detail-item">
                        <span className="pred-detail-label">Confidence</span>
                        <span className="pred-detail-value">{pred.confidence != null ? `${(pred.confidence * 100).toFixed(1)}%` : '-'}</span>
                      </div>
                      {frame && (
                        <div className="pred-detail-item">
                          <span className="pred-detail-label">Video</span>
                          <span className="pred-detail-value">{frame.video_filename || '-'}</span>
                        </div>
                      )}
                      {frame?.timestamp_sec != null && (
                        <div className="pred-detail-item">
                          <span className="pred-detail-label">Timestamp</span>
                          <span className="pred-detail-value">{frame.timestamp_sec}s</span>
                        </div>
                      )}
                    </div>
                    {propId && (
                      <button
                        className="btn btn-action btn-sm"
                        style={{ marginTop: 8, width: '100%' }}
                        onClick={(e) => { e.stopPropagation(); handleGoToProperty(propId); }}
                      >
                        View Property #{propId} on Map
                      </button>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Fullscreen Modal */}
      {modalImg && (
        <div className="frame-modal-overlay" onClick={() => setModalImg(null)}>
          <div className="frame-modal" onClick={(e) => e.stopPropagation()}>
            <button className="frame-modal-close" onClick={() => setModalImg(null)}>
              <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </button>
            <img src={modalImg.src} alt={modalImg.label} className="frame-modal-img" />
            <div className="frame-modal-info">
              <span className="frame-modal-label">{modalImg.label}</span>
              {modalImg.pred && (
                <>
                  <span className={`status-badge status-${modalImg.pred.predicted_class === 'commercial' ? 'flagged' : 'approved'}`}>
                    {modalImg.pred.predicted_class}
                  </span>
                  <span className="pred-conf-badge">
                    {((modalImg.pred.confidence || 0) * 100).toFixed(1)}%
                  </span>
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
