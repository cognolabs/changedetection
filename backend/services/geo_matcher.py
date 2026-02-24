"""Spatial matching service — links GPS-tagged frames to property polygons."""

from typing import Optional

from shapely.geometry import Point
from pyproj import Transformer

from backend.utils.geometry_utils import geojson_to_polygon
from backend.config import BUFFER_METERS


def match_frame_to_property(
    frame_lat: float,
    frame_lon: float,
    properties: list[dict],
    buffer_meters: float = BUFFER_METERS,
) -> Optional[int]:
    """
    Match a GPS point to a property polygon.
    First tries exact point-in-polygon, then buffered nearest match.

    Args:
        frame_lat: Frame GPS latitude
        frame_lon: Frame GPS longitude
        properties: List of dicts with 'id' and 'polygon_geojson' keys
        buffer_meters: Buffer distance for near-match

    Returns:
        property id or None
    """
    point = Point(frame_lon, frame_lat)  # Shapely uses (x=lon, y=lat)

    # Pass 1: Exact point-in-polygon
    for prop in properties:
        polygon = geojson_to_polygon(prop["polygon_geojson"])
        if polygon.contains(point):
            return prop["id"]

    # Pass 2: Buffered match — find nearest within buffer distance
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)

    point_utm_x, point_utm_y = to_utm.transform(frame_lon, frame_lat)
    point_utm = Point(point_utm_x, point_utm_y)

    best_id = None
    best_distance = float("inf")

    for prop in properties:
        polygon = geojson_to_polygon(prop["polygon_geojson"])
        # Project polygon centroid to UTM for distance check
        cx, cy = polygon.centroid.x, polygon.centroid.y
        cx_utm, cy_utm = to_utm.transform(cx, cy)

        # Project polygon to UTM for accurate distance
        from shapely.ops import transform as shapely_transform
        polygon_utm = shapely_transform(
            lambda x, y: to_utm.transform(x, y), polygon
        )

        dist = point_utm.distance(polygon_utm)
        if dist < buffer_meters and dist < best_distance:
            best_distance = dist
            best_id = prop["id"]

    return best_id


def batch_match_frames(
    frames: list[dict],
    properties: list[dict],
    buffer_meters: float = BUFFER_METERS,
) -> dict[int, Optional[int]]:
    """
    Match multiple frames to properties.
    Returns dict of {frame_id: property_id_or_None}.
    """
    results = {}
    for frame in frames:
        if frame.get("gps_lat") is None or frame.get("gps_lon") is None:
            results[frame["id"]] = None
            continue
        results[frame["id"]] = match_frame_to_property(
            frame["gps_lat"], frame["gps_lon"], properties, buffer_meters
        )
    return results
