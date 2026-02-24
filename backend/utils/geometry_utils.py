"""Geometry conversion utilities for KML coordinates to Shapely/GeoJSON."""

import json
from shapely.geometry import Polygon, Point, mapping, shape
from shapely.ops import transform
from pyproj import Transformer


def coords_to_polygon(coord_string: str) -> Polygon:
    """
    Convert KML coordinate string to Shapely Polygon.
    KML format: "lon,lat,alt lon,lat,alt ..."
    """
    points = []
    for coord in coord_string.strip().split():
        parts = coord.split(",")
        lon, lat = float(parts[0]), float(parts[1])
        points.append((lon, lat))
    return Polygon(points)


def polygon_to_geojson(polygon: Polygon) -> str:
    """Convert Shapely Polygon to GeoJSON string."""
    return json.dumps(mapping(polygon))


def geojson_to_polygon(geojson_str: str) -> Polygon:
    """Convert GeoJSON string to Shapely Polygon."""
    return shape(json.loads(geojson_str))


def get_centroid(polygon: Polygon) -> tuple[float, float]:
    """Return (lat, lon) centroid of a polygon. Polygon coords are (lon, lat)."""
    c = polygon.centroid
    return c.y, c.x  # lat, lon


def buffer_point_meters(lat: float, lon: float, meters: float) -> Polygon:
    """
    Create a circular buffer around a point in meter-accurate distance.
    Projects to UTM, buffers, then projects back to WGS84.
    """
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)
    to_wgs = Transformer.from_crs("EPSG:32644", "EPSG:4326", always_xy=True)

    x, y = to_utm.transform(lon, lat)
    buffered = Point(x, y).buffer(meters)
    return transform(lambda x, y: to_wgs.transform(x, y), buffered)


def project_polygon_to_utm(polygon: Polygon) -> Polygon:
    """Project a WGS84 polygon to UTM zone 44N for meter-accurate operations."""
    to_utm = Transformer.from_crs("EPSG:4326", "EPSG:32644", always_xy=True)
    return transform(lambda x, y: to_utm.transform(x, y), polygon)
