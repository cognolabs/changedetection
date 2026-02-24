"""GPS coordinate helpers and interpolation."""

import math
from typing import Optional


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two GPS coordinates."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def interpolate_gps(
    points: list[dict],
    target_time: float,
) -> Optional[tuple[float, float]]:
    """
    Interpolate GPS coordinates at a given timestamp from a sorted list of
    GPS track points [{"time": float, "lat": float, "lon": float}, ...].
    Returns (lat, lon) or None if target_time is outside the track range.
    """
    if not points or len(points) < 2:
        return None

    if target_time <= points[0]["time"]:
        return points[0]["lat"], points[0]["lon"]
    if target_time >= points[-1]["time"]:
        return points[-1]["lat"], points[-1]["lon"]

    for i in range(len(points) - 1):
        t0 = points[i]["time"]
        t1 = points[i + 1]["time"]
        if t0 <= target_time <= t1:
            if t1 == t0:
                ratio = 0
            else:
                ratio = (target_time - t0) / (t1 - t0)
            lat = points[i]["lat"] + ratio * (points[i + 1]["lat"] - points[i]["lat"])
            lon = points[i]["lon"] + ratio * (points[i + 1]["lon"] - points[i]["lon"])
            return lat, lon

    return None
