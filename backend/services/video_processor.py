"""Video frame extraction and GPS synchronization service."""

import json
import logging
import subprocess
from pathlib import Path
from typing import Optional

import cv2
import gpxpy

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
