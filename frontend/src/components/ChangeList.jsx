import React, { useState } from 'react';
import { exportChangesCsv, exportChangesGeoJSON } from '../api/client';

export default function ChangeList({ changes, selectedChange, onSelect }) {
  const [filterStatus, setFilterStatus] = useState('all');

  const filtered =
    filterStatus === 'all'
      ? changes
      : changes.filter((c) => c.status === filterStatus);

  // Sort by confidence descending (flagged first)
  const sorted = [...filtered].sort((a, b) => {
    // Flagged items first
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
          <button className="btn-sm" onClick={handleExportCsv} title="Export CSV">
            CSV
          </button>
          <button className="btn-sm" onClick={handleExportGeoJSON} title="Export GeoJSON">
            GeoJSON
          </button>
        </div>
      </div>

      {/* Table */}
      {sorted.length === 0 ? (
        <div className="empty-state-small">
          <p>No changes detected yet.</p>
          <p className="hint">
            Upload data, run inference, and detect changes to see results.
          </p>
        </div>
      ) : (
        <div className="change-table-wrapper">
          <table className="change-table">
            <thead>
              <tr>
                <th>Property</th>
                <th>Existing</th>
                <th>Predicted</th>
                <th>Conf.</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((change) => {
                const isSelected = selectedChange?.id === change.id;
                return (
                  <tr
                    key={change.id}
                    className={`change-row ${isSelected ? 'selected' : ''} ${
                      change.status === 'flagged' ? 'row-flagged' : ''
                    }`}
                    onClick={() => onSelect(change)}
                  >
                    <td className="cell-name">
                      {change.property_name || `Property ${change.property_id}`}
                    </td>
                    <td className="cell-typology">
                      {change.existing_typology || 'N/A'}
                    </td>
                    <td className="cell-typology">
                      {change.predicted_typology || 'N/A'}
                    </td>
                    <td className="cell-conf">
                      {change.aggregated_confidence != null
                        ? `${(change.aggregated_confidence * 100).toFixed(0)}%`
                        : '-'}
                    </td>
                    <td>
                      <span className={`status-badge status-${change.status}`}>
                        {change.status}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
