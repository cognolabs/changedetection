import React from 'react';
import { getFrameImageUrl } from '../api/client';

export default function FrameEvidence({ frames, predictions }) {
  if (!frames || frames.length === 0) {
    return (
      <div className="empty-state-small">
        <p>No frames linked to this property yet.</p>
        <p className="hint">Upload a video and run geo-matching to link frames.</p>
      </div>
    );
  }

  // Build prediction lookup by frame_id
  const predByFrame = {};
  (predictions || []).forEach((p) => {
    if (!predByFrame[p.frame_id]) predByFrame[p.frame_id] = [];
    predByFrame[p.frame_id].push(p);
  });

  return (
    <div className="frame-grid">
      {frames.map((frame) => {
        const preds = predByFrame[frame.id] || [];
        // Take highest confidence prediction
        const topPred = preds.sort(
          (a, b) => (b.confidence || 0) - (a.confidence || 0)
        )[0];

        return (
          <div key={frame.id} className="frame-card">
            <div className="frame-img-wrapper">
              <img
                src={getFrameImageUrl(frame.id)}
                alt={`Frame ${frame.id}`}
                className="frame-img"
                loading="lazy"
                onError={(e) => {
                  e.target.style.display = 'none';
                  e.target.nextSibling.style.display = 'flex';
                }}
              />
              <div className="frame-img-fallback" style={{ display: 'none' }}>
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                  <path d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909M3.75 21h16.5A2.25 2.25 0 0 0 22.5 18.75V5.25A2.25 2.25 0 0 0 20.25 3H3.75A2.25 2.25 0 0 0 1.5 5.25v13.5A2.25 2.25 0 0 0 3.75 21Z" />
                </svg>
              </div>
              {topPred && (
                <div className="frame-overlay">
                  <span className="pred-class">{topPred.predicted_class || topPred.label}</span>
                  <span className="pred-conf">
                    {((topPred.confidence || 0) * 100).toFixed(0)}%
                  </span>
                </div>
              )}
            </div>
            <div className="frame-meta">
              <span className="frame-id">Frame #{frame.id}</span>
              {frame.video && (
                <span className="frame-video" title={frame.video}>
                  {frame.video}
                </span>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
}
