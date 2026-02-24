import React, { useState } from 'react';

const LEGEND_ITEMS = [
  {
    color: '#f97316',
    label: 'Mismatch Flagged',
    description: 'Typology mismatch detected, awaiting review',
    pulsing: true,
  },
  {
    color: '#22c55e',
    label: 'Confirmed',
    description: 'Prediction matches GIS typology or review resolved',
  },
  {
    color: '#ef4444',
    label: 'Commercial',
    description: 'Classified as commercial in GIS data',
  },
  {
    color: '#3b82f6',
    label: 'Non-Commercial',
    description: 'Classified as residential/non-commercial in GIS data',
  },
  {
    color: '#f59e0b',
    label: 'Mixed Use',
    description: 'Classified as mixed-use in GIS data',
  },
  {
    color: '#94a3b8',
    label: 'Unanalyzed',
    description: 'No video frames analyzed for this property',
  },
];

export default function Legend() {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className={`legend ${collapsed ? 'legend-collapsed' : ''}`}>
      <button
        className="legend-toggle"
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="legend-toggle-left">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <rect x="3" y="3" width="7" height="7" rx="1" />
            <rect x="14" y="3" width="7" height="7" rx="1" />
            <rect x="3" y="14" width="7" height="7" rx="1" />
            <rect x="14" y="14" width="7" height="7" rx="1" />
          </svg>
          <span className="legend-title">Legend</span>
        </div>
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          className={`legend-chevron ${collapsed ? 'rotated' : ''}`}
        >
          <path d="m19 9-7 7-7-7" />
        </svg>
      </button>

      {!collapsed && (
        <div className="legend-items">
          {LEGEND_ITEMS.map((item) => (
            <div key={item.label} className="legend-item" title={item.description}>
              <span
                className={`legend-swatch ${item.pulsing ? 'swatch-pulsing' : ''}`}
                style={{ backgroundColor: item.color }}
              />
              <span className="legend-label">{item.label}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
