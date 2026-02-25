import React, { useState, useEffect, useCallback } from 'react';
import MapView from './components/MapView';
import PropertyPanel from './components/PropertyPanel';
import ChangeList from './components/ChangeList';
import PredictionList from './components/PredictionList';
import UploadPanel from './components/UploadPanel';
import StatusBar from './components/StatusBar';
import Legend from './components/Legend';
import {
  getPropertiesGeoJSON,
  listChanges,
  listFrames,
  listPredictions,
  listProperties,
  getChangesSummary,
} from './api/client';

export default function App() {
  // ── Data state ───────────────────────────────────────────────────────────
  const [geojson, setGeojson] = useState(null);
  const [properties, setProperties] = useState([]);
  const [changes, setChanges] = useState([]);
  const [summary, setSummary] = useState(null);
  const [frames, setFrames] = useState([]);
  const [predictions, setPredictions] = useState([]);

  // ── UI state ─────────────────────────────────────────────────────────────
  const [selectedProperty, setSelectedProperty] = useState(null);
  const [selectedChange, setSelectedChange] = useState(null);
  const [leftTab, setLeftTab] = useState('uploads'); // 'uploads' | 'changes' | 'preds'
  const [refreshKey, setRefreshKey] = useState(0);

  // ── Data loaders ─────────────────────────────────────────────────────────
  const refresh = useCallback(() => {
    setRefreshKey((k) => k + 1);
  }, []);

  useEffect(() => {
    getPropertiesGeoJSON()
      .then((r) => setGeojson(r.data))
      .catch(() => {});
    listProperties()
      .then((r) => setProperties(Array.isArray(r.data) ? r.data : []))
      .catch(() => {});
    listChanges()
      .then((r) => setChanges(Array.isArray(r.data) ? r.data : []))
      .catch(() => {});
    getChangesSummary()
      .then((r) => setSummary(r.data))
      .catch(() => {});
    listFrames()
      .then((r) => setFrames(Array.isArray(r.data) ? r.data : []))
      .catch(() => {});
    listPredictions()
      .then((r) => setPredictions(Array.isArray(r.data) ? r.data : []))
      .catch(() => {});
  }, [refreshKey]);

  // Build a lookup: property_id -> change record(s)
  const changesByProperty = {};
  changes.forEach((c) => {
    const pid = c.property_id;
    if (!changesByProperty[pid]) changesByProperty[pid] = [];
    changesByProperty[pid].push(c);
  });

  // Frames for selected property
  const propertyFrames = selectedProperty
    ? frames.filter(
        (f) =>
          f.matched_property_id === selectedProperty.id ||
          f.matched_property_id === selectedProperty.properties?.id
      )
    : [];

  // Predictions for selected property's frames
  const propertyFrameIds = new Set(propertyFrames.map((f) => f.id));
  const propertyPredictions = predictions.filter((p) =>
    propertyFrameIds.has(p.frame_id)
  );

  // Find the change record for the selected property
  const selectedPropertyId =
    selectedProperty?.id || selectedProperty?.properties?.id;
  const propertyChange = selectedPropertyId
    ? (changesByProperty[selectedPropertyId] || [])[0] || null
    : null;

  // Handle selecting a property from the map
  function handlePropertySelect(feature) {
    setSelectedProperty(feature);
    // Find matching change
    const pid = feature?.id || feature?.properties?.id;
    const matchingChange = changes.find((c) => c.property_id === pid) || null;
    setSelectedChange(matchingChange);
  }

  // Handle selecting a change from the list
  function handleChangeSelect(change) {
    setSelectedChange(change);
    // Find the matching property feature in geojson
    if (geojson && geojson.features) {
      const feature = geojson.features.find((f) => {
        const fid = f.id || f.properties?.id;
        return fid === change.property_id;
      });
      if (feature) setSelectedProperty(feature);
    }
  }

  return (
    <div className="app">
      {/* ── Left Sidebar ─────────────────────────────────────────────────── */}
      <aside className="sidebar sidebar-left">
        <div className="sidebar-header">
          <h1 className="app-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
            Change Detection
          </h1>
          <p className="app-subtitle">Property Typology System</p>
        </div>

        <div className="sidebar-tabs">
          <button
            className={`tab-btn ${leftTab === 'uploads' ? 'active' : ''}`}
            onClick={() => setLeftTab('uploads')}
          >
            Pipeline
          </button>
          <button
            className={`tab-btn ${leftTab === 'preds' ? 'active' : ''}`}
            onClick={() => setLeftTab('preds')}
          >
            Preds
            {predictions.length > 0 && (
              <span className="badge">{predictions.length}</span>
            )}
          </button>
          <button
            className={`tab-btn ${leftTab === 'changes' ? 'active' : ''}`}
            onClick={() => setLeftTab('changes')}
          >
            Changes
            {changes.filter((c) => c.status === 'flagged').length > 0 && (
              <span className="badge">
                {changes.filter((c) => c.status === 'flagged').length}
              </span>
            )}
          </button>
        </div>

        <div className="sidebar-content">
          {leftTab === 'uploads' ? (
            <UploadPanel onRefresh={refresh} />
          ) : leftTab === 'preds' ? (
            <PredictionList
              predictions={predictions}
              frames={frames}
              onSelectProperty={(propId) => {
                if (geojson && geojson.features) {
                  const feature = geojson.features.find(
                    (f) => (f.id || f.properties?.id) === propId
                  );
                  if (feature) handlePropertySelect(feature);
                }
              }}
            />
          ) : (
            <ChangeList
              changes={changes}
              selectedChange={selectedChange}
              onSelect={handleChangeSelect}
            />
          )}
        </div>

        <StatusBar
          properties={properties}
          frames={frames}
          predictions={predictions}
          changes={changes}
          summary={summary}
          onTabSelect={setLeftTab}
        />
      </aside>

      {/* ── Center Map ───────────────────────────────────────────────────── */}
      <main className="map-area">
        <MapView
          geojson={geojson}
          changes={changes}
          changesByProperty={changesByProperty}
          selectedProperty={selectedProperty}
          onPropertySelect={handlePropertySelect}
        />
        <Legend />
      </main>

      {/* ── Right Sidebar ────────────────────────────────────────────────── */}
      <aside
        className={`sidebar sidebar-right ${selectedProperty ? 'open' : ''}`}
      >
        {selectedProperty ? (
          <PropertyPanel
            property={selectedProperty}
            change={propertyChange}
            frames={propertyFrames}
            predictions={propertyPredictions}
            onClose={() => {
              setSelectedProperty(null);
              setSelectedChange(null);
            }}
            onRefresh={refresh}
          />
        ) : (
          <div className="panel-empty">
            <div className="panel-empty-icon">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
                <path d="M15 10.5a3 3 0 1 1-6 0 3 3 0 0 1 6 0Z" />
                <path d="M19.5 10.5c0 7.142-7.5 11.25-7.5 11.25S4.5 17.642 4.5 10.5a7.5 7.5 0 1 1 15 0Z" />
              </svg>
            </div>
            <p>Select a property on the map to view details</p>
          </div>
        )}
      </aside>
    </div>
  );
}
