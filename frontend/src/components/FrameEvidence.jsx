import React, { useState } from 'react';
import { getPredictionImageUrl, getFrameImageUrl } from '../api/client';

export default function FrameEvidence({ frames, predictions }) {
  const [modalImg, setModalImg] = useState(null);

  if (!frames || frames.length === 0) {
    return (
      <div className="empty-state-small">
        <p>No frames linked to this property yet.</p>
        <p className="hint">Upload a video and run geo-matching to link frames.</p>
      </div>
    );
  }

  // Build prediction lookup by frame_id (keep highest confidence per frame)
  const predByFrame = {};
  (predictions || []).forEach((p) => {
    if (!predByFrame[p.frame_id] || p.confidence > predByFrame[p.frame_id].confidence) {
      predByFrame[p.frame_id] = p;
    }
  });

  return (
    <>
      <div className="frame-grid">
        {frames.map((frame) => {
          const topPred = predByFrame[frame.id];
          // Use prediction image (with bounding box) if available, else raw frame
          const imgSrc = topPred
            ? getPredictionImageUrl(topPred.id)
            : getFrameImageUrl(frame.id);

          return (
            <div
              key={frame.id}
              className="frame-card"
              onClick={() => setModalImg({ src: imgSrc, label: `Frame #${frame.id}`, pred: topPred })}
              style={{ cursor: 'pointer' }}
            >
              <div className="frame-img-wrapper">
                <img
                  src={imgSrc}
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
                    <span className="pred-class">{topPred.predicted_class}</span>
                    <span className="pred-conf">
                      {((topPred.confidence || 0) * 100).toFixed(0)}%
                    </span>
                  </div>
                )}
              </div>
              <div className="frame-meta">
                <span className="frame-id">Frame #{frame.id}</span>
              </div>
            </div>
          );
        })}
      </div>

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
    </>
  );
}
