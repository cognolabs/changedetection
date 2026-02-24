import React from 'react';
import FrameEvidence from './FrameEvidence';
import ReviewActions from './ReviewActions';

function computeCentroid(feature) {
  try {
    const geom = feature.geometry;
    if (!geom) return null;

    let coords = [];
    if (geom.type === 'Point') {
      return { lng: geom.coordinates[0], lat: geom.coordinates[1] };
    } else if (geom.type === 'Polygon') {
      coords = geom.coordinates[0];
    } else if (geom.type === 'MultiPolygon') {
      coords = geom.coordinates[0][0];
    } else {
      return null;
    }

    let latSum = 0;
    let lngSum = 0;
    coords.forEach(([lng, lat]) => {
      latSum += lat;
      lngSum += lng;
    });
    return {
      lat: (latSum / coords.length).toFixed(6),
      lng: (lngSum / coords.length).toFixed(6),
    };
  } catch {
    return null;
  }
}

export default function PropertyPanel({
  property,
  change,
  frames,
  predictions,
  onClose,
  onRefresh,
}) {
  const props = property?.properties || property || {};
  const name = props.name || props.property_name || props.id || 'Unknown Property';
  const typology = props.existing_typology || props.typology || 'N/A';
  const centroid = computeCentroid(property);

  return (
    <div className="property-panel">
      <div className="property-panel-header">
        <div>
          <h2 className="property-panel-title">{name}</h2>
          <span className="property-panel-typology">{typology}</span>
        </div>
        <button className="btn-icon" onClick={onClose} title="Close">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>

      <div className="property-panel-body">
        {/* Details Section */}
        <section className="panel-section">
          <h3 className="section-title">Details</h3>
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">ID</span>
              <span className="detail-value">{props.id || 'N/A'}</span>
            </div>
            <div className="detail-item">
              <span className="detail-label">Typology</span>
              <span className="detail-value">{typology}</span>
            </div>
            {centroid && (
              <>
                <div className="detail-item">
                  <span className="detail-label">Latitude</span>
                  <span className="detail-value">{centroid.lat}</span>
                </div>
                <div className="detail-item">
                  <span className="detail-label">Longitude</span>
                  <span className="detail-value">{centroid.lng}</span>
                </div>
              </>
            )}
            {props.area && (
              <div className="detail-item">
                <span className="detail-label">Area</span>
                <span className="detail-value">{props.area}</span>
              </div>
            )}
          </div>
        </section>

        {/* Change Detection Status */}
        {change && (
          <section className="panel-section">
            <h3 className="section-title">Change Detection</h3>
            <div className="change-card">
              <div className="change-card-row">
                <span className="change-label">Status</span>
                <span className={`status-badge status-${change.status}`}>
                  {change.status}
                </span>
              </div>
              <div className="change-card-row">
                <span className="change-label">GIS Typology</span>
                <span className="change-value">
                  {change.existing_typology || typology}
                </span>
              </div>
              <div className="change-card-row">
                <span className="change-label">Predicted</span>
                <span className="change-value">
                  {change.predicted_typology || 'N/A'}
                </span>
              </div>
              {change.aggregated_confidence != null && (
                <div className="change-card-row">
                  <span className="change-label">Confidence</span>
                  <span className="change-value">
                    {(change.aggregated_confidence * 100).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>
          </section>
        )}

        {/* Frame Evidence */}
        <section className="panel-section">
          <h3 className="section-title">
            Frame Evidence
            {frames.length > 0 && (
              <span className="count-label">{frames.length} frames</span>
            )}
          </h3>
          <FrameEvidence frames={frames} predictions={predictions} />
        </section>

        {/* Review Actions */}
        {change && change.status === 'flagged' && (
          <section className="panel-section">
            <h3 className="section-title">Review</h3>
            <ReviewActions change={change} onRefresh={onRefresh} />
          </section>
        )}
      </div>
    </div>
  );
}
