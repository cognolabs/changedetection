import React from 'react';

export default function StatusBar({
  properties,
  frames,
  predictions,
  changes,
  summary,
  onTabSelect,
}) {
  const propCount = properties?.length || 0;
  const frameCount = frames?.length || 0;
  const predCount = predictions?.length || 0;
  const changeCount = changes?.length || 0;
  const flaggedCount = changes?.filter((c) => c.status === 'flagged').length || 0;

  const items = [
    {
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>
      ),
      count: propCount,
      label: 'Properties',
      tab: 'uploads',
    },
    {
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="2" y="2" width="20" height="20" rx="2.18" ry="2.18"/><line x1="7" y1="2" x2="7" y2="22"/><line x1="17" y1="2" x2="17" y2="22"/><line x1="2" y1="12" x2="22" y2="12"/></svg>
      ),
      count: frameCount,
      label: 'Frames',
      tab: 'uploads',
    },
    {
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/></svg>
      ),
      count: predCount,
      label: 'Preds',
      tab: 'preds',
    },
    {
      icon: (
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
      ),
      count: changeCount,
      label: 'Changes',
      tab: 'changes',
    },
  ];

  return (
    <div className="status-bar">
      <div className="status-grid">
        {items.map((item) => (
          <div
            className="status-item"
            key={item.label}
            style={{ cursor: 'pointer' }}
            onClick={() => onTabSelect && onTabSelect(item.tab)}
          >
            <span className="status-icon">{item.icon}</span>
            <span className="status-count">{item.count}</span>
            <span className="status-label">{item.label}</span>
          </div>
        ))}
        {flaggedCount > 0 && (
          <div className="status-item status-item-flagged">
            <span className="status-icon">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>
            </span>
            <span className="status-count">{flaggedCount}</span>
            <span className="status-label">Flagged</span>
          </div>
        )}
      </div>
      {summary && (summary.total_properties != null || summary.mismatches != null) && (
        <div className="status-summary">
          {summary.total_properties != null && (
            <span>Total: {summary.total_properties}</span>
          )}
          {summary.mismatches != null && (
            <span className="summary-mismatch">Mismatches: {summary.mismatches}</span>
          )}
        </div>
      )}
    </div>
  );
}
