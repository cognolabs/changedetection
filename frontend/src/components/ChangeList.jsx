import React, { useState } from 'react';
import { exportChangesCsv, exportChangesGeoJSON } from '../api/client';

export default function ChangeList({ changes, selectedChange, onSelect }) {
  const [filterStatus, setFilterStatus] = useState('all');
  const [expandedId, setExpandedId] = useState(null);

  const filtered =
    filterStatus === 'all'
      ? changes
      : changes.filter((c) => c.status === filterStatus);

  const sorted = [...filtered].sort((a, b) => {
    if (a.status === 'flagged' && b.status !== 'flagged') return -1;
    if (b.status === 'flagged' && a.status !== 'flagged') return 1;
    return (b.aggregated_confidence || 0) - (a.aggregated_confidence || 0);
  });

  function handleExportCsv() {
    exportChangesCsv()
      .then((res) => {
        const url = URL.createObjectURL(res.data);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'changes.csv';
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => alert('Failed to export CSV'));
  }

  function handleExportGeoJSON() {
    exportChangesGeoJSON()
      .then((res) => {
        const url = URL.createObjectURL(res.data);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'changes.geojson';
        a.click();
        URL.revokeObjectURL(url);
      })
      .catch(() => alert('Failed to export GeoJSON'));
  }

  return (
    <div className="change-list">
      {/* Filter Bar */}
      <div className="change-list-header">
        <div className="filter-group">
          {['all', 'flagged', 'approved', 'rejected'].map((s) => (
            <button
              key={s}
              className={`filter-btn ${filterStatus === s ? 'active' : ''}`}
              onClick={() => setFilterStatus(s)}
            >
              {s.charAt(0).toUpperCase() + s.slice(1)}
              {s !== 'all' && (
                <span className="filter-count">
                  {changes.filter((c) => c.status === s).length}
                </span>
              )}
            </button>
          ))}
        </div>
        <div className="export-group">
          <button className="btn-sm" onClick={handleExportCsv} title="Export CSV">CSV</button>
          <button className="btn-sm" onClick={handleExportGeoJSON} title="Export GeoJSON">GeoJSON</button>
        </div>
      </div>

      {/* Cards */}
      {sorted.length === 0 ? (
        <div className="empty-state-small">
          <p>No changes detected yet.</p>
          <p className="hint">
            Upload data, run inference, and detect changes to see results.
          </p>
        </div>
      ) : (
        <div className="pred-list-wrapper">
          {sorted.map((change) => {
            const isExpanded = expandedId === change.id;
            const isSelected = selectedChange?.id === change.id;
            return (
              <div
                key={change.id}
                className={`pred-card ${isExpanded ? 'pred-card-expanded' : ''} ${isSelected ? 'pred-card-selected' : ''}`}
              >
                <div
                  className="pred-card-header"
                  onClick={() => {
                    setExpandedId(isExpanded ? null : change.id);
                    onSelect(change);
                  }}
                >
                  <div className="pred-card-left">
                    <span className="pred-frame-id">
                      {change.property_name || `Property #${change.property_id}`}
                    </span>
                    <span className="pred-prop-id">
                      {change.existing_typology || 'N/A'} &rarr; {change.predicted_typology || 'N/A'}
                    </span>
                  </div>
                  <div className="pred-card-right">
                    <span className={`status-badge status-${change.status}`}>
                      {change.status}
                    </span>
                    <span className="pred-conf-badge">
                      {change.aggregated_confidence != null
                        ? `${(change.aggregated_confidence * 100).toFixed(0)}%`
                        : '-'}
                    </span>
                  </div>
                </div>

                {isExpanded && (
                  <div className="pred-card-body">
                    <div className="pred-detail-grid">
                      <div className="pred-detail-item">
                        <span className="pred-detail-label">Existing</span>
                        <span className="pred-detail-value">{change.existing_typology || 'N/A'}</span>
                      </div>
                      <div className="pred-detail-item">
                        <span className="pred-detail-label">Predicted</span>
                        <span className="pred-detail-value">{change.predicted_typology || 'N/A'}</span>
                      </div>
                      <div className="pred-detail-item">
                        <span className="pred-detail-label">Confidence</span>
                        <span className="pred-detail-value">
                          {change.aggregated_confidence != null
                            ? `${(change.aggregated_confidence * 100).toFixed(1)}%`
                            : '-'}
                        </span>
                      </div>
                      <div className="pred-detail-item">
                        <span className="pred-detail-label">Frames</span>
                        <span className="pred-detail-value">
                          {change.num_frames_agreeing}/{change.num_frames_analyzed} agreeing
                        </span>
                      </div>
                      {change.reviewed_by && (
                        <div className="pred-detail-item">
                          <span className="pred-detail-label">Reviewed by</span>
                          <span className="pred-detail-value">{change.reviewed_by}</span>
                        </div>
                      )}
                      {change.review_notes && (
                        <div className="pred-detail-item">
                          <span className="pred-detail-label">Notes</span>
                          <span className="pred-detail-value">{change.review_notes}</span>
                        </div>
                      )}
                    </div>
                    <button
                      className="btn btn-action btn-sm"
                      style={{ marginTop: 8, width: '100%' }}
                      onClick={(e) => { e.stopPropagation(); onSelect(change); }}
                    >
                      View on Map
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
