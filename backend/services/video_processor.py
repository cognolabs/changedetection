"""Video frame extraction and GPS synchronization service."""

import json
import logging
import subprocess
import zipfile
from pathlib import Path
from typing import Optional

import cv2
import gpxpy
from lxml import etree

from backend.config import FRAMES_DIR, FRAME_INTERVAL_SEC
from backend.utils.gps_utils import interpolate_gps

logger = logging.getLogger(__name__)


def extract_frames(
    video_path: Path,
    interval_sec: float = FRAME_INTERVAL_SEC,
) -> list[dict]:
    """
    Extract frames from video at given interval.
    Returns list of dicts: {frame_number, timestamp_sec, frame_path}
    """
    logger.info("Opening video: %s", video_path.name)
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0:
        fps = 30.0
    frame_skip = max(1, int(fps * interval_sec))

    video_name = video_path.stem
    output_dir = FRAMES_DIR / video_name
    output_dir.mkdir(parents=True, exist_ok=True)

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_sec = total_frames / fps
    expected = total_frames // frame_skip
    logger.info(
        "Video info: %.1f fps, %d total frames, %.1fs duration, extracting ~%d frames",
        fps, total_frames, duration_sec, expected,
    )

    frames = []
    extracted_count = 0
    frame_idx = 0

    while frame_idx < total_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
        ret, frame = cap.read()
        if not ret:
            logger.warning("Failed to read frame at index %d, stopping", frame_idx)
            break

        timestamp_sec = frame_idx / fps
        frame_filename = f"{video_name}_frame_{extracted_count:05d}.jpg"
        frame_path = output_dir / frame_filename
        cv2.imwrite(str(frame_path), frame)

        extracted_count += 1
        if extracted_count % 50 == 0 or extracted_count == 1:
            logger.info(
                "Extracted %d/%d frames (%.0f%%)",
                extracted_count, expected, extracted_count / expected * 100 if expected else 0,
            )

        frames.append({
            "video_filename": video_path.name,
            "frame_number": extracted_count - 1,
            "timestamp_sec": round(timestamp_sec, 3),
            "frame_path": str(frame_path.relative_to(FRAMES_DIR)),
        })
        frame_idx += frame_skip

    cap.release()
    logger.info("Extraction complete: %d frames saved to %s", extracted_count, output_dir)
    return frames


def extract_gps_from_video(video_path: Path) -> list[dict]:
    """
    Try to extract GPS telemetry from video using ffprobe.
    Returns list of {time, lat, lon} or empty list.
    """
    try:
        result = subprocess.run(
            [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_entries", "stream_tags",
                str(video_path),
            ],
            capture_output=True, text=True, timeout=30,
        )
        # Parse output for GPS data if available
        data = json.loads(result.stdout)
        # Most consumer videos don't embed GPS as stream metadata in a
        # standardized way, so this is best-effort.
        # For GoPro / DJI, specialized parsers would be needed.
        return []
    except (subprocess.SubprocessError, json.JSONDecodeError, FileNotFoundError):
        return []


def parse_gpx_file(gpx_path: Path) -> list[dict]:
    """
    Parse a GPX file into a list of {time, lat, lon} track points,
    with time as seconds from track start.
    """
    with open(gpx_path, "r", encoding="utf-8") as f:
        gpx = gpxpy.parse(f)

    points = []
    start_time = None

    for track in gpx.tracks:
        for segment in track.segments:
            for pt in segment.points:
                if pt.time is None:
                    continue
                if start_time is None:
                    start_time = pt.time
                elapsed = (pt.time - start_time).total_seconds()
                points.append({
                    "time": elapsed,
                    "lat": pt.latitude,
                    "lon": pt.longitude,
                })

    return points


def parse_kml_track(kml_path: Path) -> list[dict]:
    """
    Parse a KML or KMZ file and extract GPS track points.
    Supports:
      - <gx:Track> with <when> + <gx:coord> elements
      - <LineString><coordinates> (evenly spaced, no timestamps)
    Handles KML files with or without XML namespaces.
    Returns list of {time, lat, lon} with time as seconds from start.
    """
    suffix = kml_path.suffix.lower()

    if suffix == ".kmz":
        with zipfile.ZipFile(kml_path, "r") as zf:
            kml_name = next(
                (n for n in zf.namelist() if n.lower().endswith(".kml")),
                None,
            )
            if not kml_name:
                return []
            kml_bytes = zf.read(kml_name)
    else:
        kml_bytes = kml_path.read_bytes()

    root = etree.fromstring(kml_bytes)
    points: list[dict] = []

    def find_all_local(parent, tag):
        """Find all descendants matching local tag name regardless of namespace."""
        return [e for e in parent.iter() if etree.QName(e.tag).localname == tag]

    # Method 1: gx:Track with <when> and <gx:coord>
    for track in find_all_local(root, "Track"):
        whens = find_all_local(track, "when")
        coords = find_all_local(track, "coord")

        if whens and coords and len(whens) == len(coords):
            from datetime import datetime
            start_time = None
            for w, c in zip(whens, coords):
                try:
                    ts_str = w.text.strip()
                    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
                    parts = c.text.strip().split()
                    lon, lat = float(parts[0]), float(parts[1])
                    if start_time is None:
                        start_time = ts
                    elapsed = (ts - start_time).total_seconds()
                    points.append({"time": elapsed, "lat": lat, "lon": lon})
                except (ValueError, IndexError):
                    continue
            if points:
                logger.info("Parsed gx:Track from KML: %d points", len(points))
                return points

    # Method 2: LineString coordinates (no timestamps — distribute evenly)
    for ls in find_all_local(root, "LineString"):
        coord_els = find_all_local(ls, "coordinates")
        for coord_el in coord_els:
            if coord_el.text is None:
                continue
            raw_coords = coord_el.text.strip().split()
            parsed = []
            for c in raw_coords:
                parts = c.split(",")
                if len(parts) >= 2:
                    try:
                        lon, lat = float(parts[0]), float(parts[1])
                        parsed.append((lat, lon))
                    except ValueError:
                        continue
            if len(parsed) >= 2:
                for i, (lat, lon) in enumerate(parsed):
                    points.append({"time": float(i), "lat": lat, "lon": lon})
                logger.info("Parsed LineString from KML: %d coordinate points", len(points))
                return points

    logger.warning("No track data found in KML file: %s", kml_path.name)
    return points


def parse_track_file(file_path: Path) -> list[dict]:
    """Parse any supported GPS track file (.gpx, .kml, .kmz) into track points."""
    suffix = file_path.suffix.lower()
    if suffix == ".gpx":
        return parse_gpx_file(file_path)
    elif suffix in (".kml", ".kmz"):
        return parse_kml_track(file_path)
    return []


def assign_gps_to_frames(
    frames: list[dict],
    gps_points: list[dict],
) -> list[dict]:
    """
    Assign GPS coordinates to frames by interpolating from GPS track points.
    Modifies frames in-place and returns them.
    """
    if not gps_points:
        return frames

    for frame in frames:
        result = interpolate_gps(gps_points, frame["timestamp_sec"])
        if result:
            frame["gps_lat"], frame["gps_lon"] = result
            frame["gps_source"] = "gpx_interpolated"

    return frames
