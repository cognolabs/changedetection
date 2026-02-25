"""Spatial matching service — links GPS-tagged frames to property polygons."""

import json
import logging
from typing import Optional

from shapely.geometry import Point, shape
from shapely import STRtree
from pyproj import Transformer

from backend.config import BUFFER_METERS

logger = logging.getLogger(__name__)


def _build_index(properties: list[dict]):
    """
    Pre-parse polygons and build a spatial index.
    Returns (polygons, prop_ids, strtree).
    """
    polygons = []
    prop_ids = []
    for prop in properties:
        try:
            geom = shape(json.loads(prop["polygon_geojson"]))
            polygons.append(geom)
            prop_ids.append(prop["id"])
        except Exception:
            continue
    tree = STRtree(polygons)
    return polygons, prop_ids, tree


def match_frames_to_properties(
    frames: list[dict],
    properties: list[dict],
    buffer_meters: float = BUFFER_METERS,
) -> dict[int, Optional[int]]:
    """
    Match multiple GPS-tagged frames to property polygons efficiently.
    Uses spatial index for fast lookup.

    Args:
        frames: list of dicts with 'id', 'gps_lat', 'gps_lon'
        properties: list of dicts with 'id', 'polygon_geojson'
        buffer_meters: buffer distance for near-match

    Returns:
        dict of {frame_id: property_id or None}
    """
    if not properties or not frames:
        return {}

    polygons, prop_ids, tree = _build_index(properties)
    logger.info("Spatial index built: %d polygons", len(polygons))

    # Pre-compute buffered polygons for pass 2 (union each polygon with its buffer)
    # Use approximate degree buffer for initial candidate search
    # At ~25°N latitude: 1 degree ≈ 111km, so buffer_meters in degrees:
    degree_buffer = buffer_meters / 111_000  # rough approximation for candidate filter

    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)

    results = {}
    matched = 0

    for frame in frames:
        lat = frame.get("gps_lat")
        lon = frame.get("gps_lon")
        if lat is None or lon is None:
            results[frame["id"]] = None
            continue

        point = Point(lon, lat)

        # Pass 1: Exact point-in-polygon using spatial index
        candidates = tree.query(point)
        found = None
        for idx in candidates:
            if polygons[idx].contains(point):
                found = prop_ids[idx]
                break

        if found is not None:
            results[frame["id"]] = found
            matched += 1
            continue

        # Pass 2: Buffered search — expand search area
        search_area = point.buffer(degree_buffer)
        nearby = tree.query(search_area)

        if len(nearby) == 0:
            results[frame["id"]] = None
            continue

        # Use UTM for accurate distance
        px, py = to_utm.transform(lon, lat)
        point_utm = Point(px, py)

        best_id = None
        best_dist = float("inf")

        for idx in nearby:
            poly = polygons[idx]
            # Project just the nearest point for distance check
            cx, cy = poly.centroid.x, poly.centroid.y
            cx_utm, cy_utm = to_utm.transform(cx, cy)

            # Quick centroid distance filter
            approx_dist = point_utm.distance(Point(cx_utm, cy_utm))
            if approx_dist > buffer_meters * 3:
                continue

            # Accurate edge distance using nearest points on polygon boundary
            nearest_pt = poly.boundary.interpolate(poly.boundary.project(point))
            nx, ny = to_utm.transform(nearest_pt.x, nearest_pt.y)
            dist = point_utm.distance(Point(nx, ny))

            if dist < buffer_meters and dist < best_dist:
                best_dist = dist
                best_id = prop_ids[idx]

        results[frame["id"]] = best_id
        if best_id is not None:
            matched += 1

    logger.info("Matching complete: %d/%d frames matched", matched, len(frames))
    return results


# Keep backwards-compatible single-frame function
def match_frame_to_property(
    frame_lat: float,
    frame_lon: float,
    properties: list[dict],
    buffer_meters: float = BUFFER_METERS,
) -> Optional[int]:
    """Match a single GPS point to a property polygon."""
    result = match_frames_to_properties(
        [{"id": 0, "gps_lat": frame_lat, "gps_lon": frame_lon}],
        properties,
        buffer_meters,
    )
    return result.get(0)
