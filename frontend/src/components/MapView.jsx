import React, { useState, useEffect, useRef, useMemo } from 'react';
import { MapContainer, TileLayer, GeoJSON, LayersControl, useMap } from 'react-leaflet';

// Color helper based on change status and typology
function getFeatureStyle(feature, changesByProperty) {
  const pid = feature.id || feature.properties?.id;
  const changes = changesByProperty[pid];
  const typology = (feature.properties?.existing_typology || feature.properties?.typology || '').toLowerCase();

  let fillColor = '#94a3b8'; // gray — no data
  let className = '';

  if (changes && changes.length > 0) {
    const latestChange = changes[0];
    if (latestChange.status === 'flagged') {
      fillColor = '#f97316'; // orange
      className = 'polygon-flagged';
    } else if (
      latestChange.status === 'approved' ||
      latestChange.status === 'confirmed'
    ) {
      fillColor = '#22c55e'; // green
    } else if (latestChange.status === 'rejected') {
      fillColor = '#22c55e'; // green (rejected mismatch = confirmed)
    }
  } else {
    // Color by GIS typology
    if (typology === 'mix' || typology === 'mixed') {
      fillColor = '#f59e0b'; // amber — mix
    } else if (
      typology.includes('commercial') ||
      typology.includes('business') ||
      typology.includes('retail') ||
      typology.includes('industrial')
    ) {
      fillColor = '#ef4444'; // red — commercial
    } else if (
      typology.includes('residential') ||
      typology.includes('dwelling') ||
      typology.includes('house') ||
      typology.includes('flat')
    ) {
      fillColor = '#3b82f6'; // blue — non-commercial
    }
  }

  return {
    color: '#1e293b',
    weight: 1.5,
    opacity: 0.8,
    fillColor,
    fillOpacity: 0.55,
    className,
  };
}

// Sub-component to fit bounds when geojson changes
function FitBounds({ geojson }) {
  const map = useMap();
  useEffect(() => {
    if (!geojson || !geojson.features || geojson.features.length === 0) return;
    try {
      const L = window.L || require('leaflet');
      const layer = L.geoJSON(geojson);
      const bounds = layer.getBounds();
      if (bounds.isValid()) {
        map.fitBounds(bounds, { padding: [40, 40] });
      }
    } catch {
      // ignore
    }
  }, [geojson, map]);
  return null;
}

// Sub-component to fly to selected property
function FlyToSelected({ selectedProperty }) {
  const map = useMap();
  useEffect(() => {
    if (!selectedProperty) return;
    try {
      const L = window.L || require('leaflet');
      const layer = L.geoJSON(selectedProperty);
      const bounds = layer.getBounds();
      if (bounds.isValid()) {
        map.flyToBounds(bounds, { padding: [80, 80], maxZoom: 18, duration: 0.6 });
      }
    } catch {
      // ignore
    }
  }, [selectedProperty, map]);
  return null;
}

export default function MapView({
  geojson,
  changes,
  changesByProperty,
  selectedProperty,
  onPropertySelect,
}) {
  const geoJsonRef = useRef(null);

  // Re-key GeoJSON layer when data or changes update
  const geoKey = useMemo(() => {
    return JSON.stringify({
      fc: geojson?.features?.length || 0,
      cc: changes?.length || 0,
      cs: changes?.map((c) => c.status).join(',') || '',
    });
  }, [geojson, changes]);

  function onEachFeature(feature, layer) {
    const props = feature.properties || {};
    const name = props.name || props.property_name || props.id || 'Unknown';
    const typology = props.existing_typology || props.typology || 'N/A';

    layer.bindTooltip(
      `<strong>${name}</strong><br/>Typology: ${typology}`,
      { sticky: true, className: 'map-tooltip' }
    );

    layer.on('click', () => {
      onPropertySelect(feature);
    });
  }

  function styleFeature(feature) {
    return getFeatureStyle(feature, changesByProperty || {});
  }

  return (
    <MapContainer
      center={[25.458, 81.862]}
      zoom={12}
      className="leaflet-map"
      zoomControl={true}
    >
      <LayersControl position="topright">
        <LayersControl.BaseLayer name="OpenStreetMap" checked>
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="Satellite">
          <TileLayer
            attribution='&copy; Esri'
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"
          />
        </LayersControl.BaseLayer>
        <LayersControl.BaseLayer name="CARTO Light">
          <TileLayer
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
            url="https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
          />
        </LayersControl.BaseLayer>
      </LayersControl>

      {geojson && geojson.features && geojson.features.length > 0 && (
        <GeoJSON
          key={geoKey}
          ref={geoJsonRef}
          data={geojson}
          style={styleFeature}
          onEachFeature={onEachFeature}
        />
      )}

      <FitBounds geojson={geojson} />
      <FlyToSelected selectedProperty={selectedProperty} />
    </MapContainer>
  );
}
