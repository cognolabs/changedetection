"""Videos router — upload, frame extraction, GPS matching."""

import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import UPLOAD_DIR, FRAMES_DIR
from backend.models import VideoFrame, Property
from backend.schemas import VideoFrameOut, StatusResponse
from backend.services.video_processor import (
    extract_frames,
    extract_gps_from_video,
    parse_gpx_file,
    assign_gps_to_frames,
)
from backend.services.geo_matcher import match_frame_to_property

router = APIRouter()

# Store GPX tracks in memory for the session (keyed by video name)
_gpx_tracks: dict[str, list[dict]] = {}


@router.post("/upload", response_model=StatusResponse)
async def upload_video(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a video file for frame extraction."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    upload_path = UPLOAD_DIR / file.filename
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return StatusResponse(
        status="success",
        message=f"Video uploaded: {file.filename}",
        detail={"file": file.filename, "path": str(upload_path)},
    )


@router.post("/extract-frames", response_model=StatusResponse)
def extract_video_frames(
    video_filename: str = Query(..., description="Name of uploaded video file"),
    interval: float = Query(1.0, description="Seconds between frames"),
    db: Session = Depends(get_db),
):
    """Extract frames from an uploaded video."""
    video_path = UPLOAD_DIR / video_filename
    if not video_path.exists():
        raise HTTPException(404, f"Video file not found: {video_filename}")

    # Extract frames
    frames = extract_frames(video_path, interval_sec=interval)

    # Try to get GPS from video
    gps_points = extract_gps_from_video(video_path)

    # Use GPX track if available
    if not gps_points and video_path.stem in _gpx_tracks:
        gps_points = _gpx_tracks[video_path.stem]

    # Assign GPS to frames
    if gps_points:
        frames = assign_gps_to_frames(frames, gps_points)

    # Save to database
    for frame_data in frames:
        frame = VideoFrame(**frame_data)
        db.add(frame)

    db.commit()

    return StatusResponse(
        status="success",
        message=f"Extracted {len(frames)} frames from {video_filename}",
        detail={
            "count": len(frames),
            "gps_available": bool(gps_points),
            "video": video_filename,
        },
    )


@router.post("/upload-gpx", response_model=StatusResponse)
async def upload_gpx(
    file: UploadFile = File(...),
    video_name: str = Query(..., description="Video filename this GPX track belongs to"),
):
    """Upload a companion GPX track for a video."""
    if not file.filename or not file.filename.lower().endswith(".gpx"):
        raise HTTPException(400, "File must be .gpx")

    gpx_path = UPLOAD_DIR / file.filename
    with open(gpx_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    points = parse_gpx_file(gpx_path)
    video_stem = Path(video_name).stem
    _gpx_tracks[video_stem] = points

    return StatusResponse(
        status="success",
        message=f"GPX loaded: {len(points)} track points for {video_name}",
        detail={"points": len(points), "video": video_name},
    )


@router.get("/frames", response_model=list[VideoFrameOut])
def list_frames(
    property_id: int | None = Query(None),
    video: str | None = Query(None),
    has_gps: bool | None = Query(None),
    db: Session = Depends(get_db),
):
    """List extracted frames with optional filters."""
    query = db.query(VideoFrame)
    if property_id is not None:
        query = query.filter(VideoFrame.matched_property_id == property_id)
    if video:
        query = query.filter(VideoFrame.video_filename == video)
    if has_gps is True:
        query = query.filter(VideoFrame.gps_lat.isnot(None))
    elif has_gps is False:
        query = query.filter(VideoFrame.gps_lat.is_(None))
    return query.all()


@router.get("/frames/{frame_id}/image")
def get_frame_image(frame_id: int, db: Session = Depends(get_db)):
    """Serve a frame image file."""
    frame = db.query(VideoFrame).filter(VideoFrame.id == frame_id).first()
    if not frame:
        raise HTTPException(404, "Frame not found")

    full_path = FRAMES_DIR / frame.frame_path
    if not full_path.exists():
        raise HTTPException(404, "Frame file not found on disk")

    return FileResponse(str(full_path), media_type="image/jpeg")


@router.post("/frames/geo-match", response_model=StatusResponse)
def geo_match_frames(
    buffer_meters: float = Query(30.0, description="Buffer distance in meters"),
    db: Session = Depends(get_db),
):
    """Run spatial matching to link GPS-tagged frames to properties."""
    # Get all frames with GPS but no property match
    frames = (
        db.query(VideoFrame)
        .filter(VideoFrame.gps_lat.isnot(None))
        .filter(VideoFrame.matched_property_id.is_(None))
        .all()
    )

    if not frames:
        return StatusResponse(status="info", message="No unmatched GPS frames found")

    # Get all properties
    properties = db.query(Property).all()
    if not properties:
        return StatusResponse(status="info", message="No properties in database")

    prop_dicts = [
        {"id": p.id, "polygon_geojson": p.polygon_geojson}
        for p in properties
    ]

    matched_count = 0
    for frame in frames:
        prop_id = match_frame_to_property(
            frame.gps_lat, frame.gps_lon, prop_dicts, buffer_meters
        )
        if prop_id is not None:
            frame.matched_property_id = prop_id
            matched_count += 1

    db.commit()

    return StatusResponse(
        status="success",
        message=f"Matched {matched_count}/{len(frames)} frames to properties",
        detail={"matched": matched_count, "total": len(frames)},
    )
