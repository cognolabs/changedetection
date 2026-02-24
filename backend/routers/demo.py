"""Demo router — seed realistic demo data for Prayagraj Civil Lines."""

import json
import math
import random
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import FRAMES_DIR
from backend.models import Property, VideoFrame, Prediction, ChangeReport
from backend.schemas import StatusResponse

router = APIRouter()

# ---------------------------------------------------------------------------
# KMZ LineString coordinates (extracted from "Civil line.kmz")
# ---------------------------------------------------------------------------

def _load_route_coords() -> list[tuple[float, float]]:
    """Load coordinates from the Civil line.kmz file, or fall back to hardcoded samples."""
    kmz_path = Path(__file__).resolve().parent.parent.parent / "Civil line.kmz"
    if kmz_path.exists():
        try:
            from lxml import etree

            KML_NS = "{http://www.opengis.net/kml/2.2}"
            with zipfile.ZipFile(kmz_path, "r") as zf:
                kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
                if kml_names:
                    kml_bytes = zf.read(kml_names[0])
                    root = etree.fromstring(kml_bytes)
                    for el in root.iter():
                        if "coordinates" in el.tag.lower() and el.text:
                            coords = []
                            for c in el.text.strip().split():
                                parts = c.split(",")
                                if len(parts) >= 2:
                                    coords.append((float(parts[0]), float(parts[1])))
                            if len(coords) > 20:
                                return coords
        except Exception:
            pass

    # Fallback: hardcoded sample points along Civil Lines route
    return [
        (81.8627, 25.4588), (81.8624, 25.4586), (81.8620, 25.4584),
        (81.8616, 25.4581), (81.8613, 25.4578), (81.8609, 25.4576),
        (81.8605, 25.4573), (81.8601, 25.4570), (81.8597, 25.4567),
        (81.8593, 25.4564), (81.8589, 25.4561), (81.8585, 25.4558),
        (81.8581, 25.4555), (81.8576, 25.4552), (81.8572, 25.4549),
        (81.8568, 25.4546), (81.8564, 25.4543), (81.8560, 25.4540),
        (81.8556, 25.4537), (81.8552, 25.4534),
    ]


def _sample_evenly(coords: list[tuple[float, float]], n: int) -> list[tuple[float, float]]:
    """Pick n evenly-spaced points from a coordinate list."""
    if len(coords) <= n:
        return coords
    step = (len(coords) - 1) / (n - 1)
    return [coords[round(i * step)] for i in range(n)]


def _make_rect_polygon(lon: float, lat: float, offset_lon: float = 0.00015,
                        offset_lat: float = 0.00008) -> dict:
    """Create a small rectangular GeoJSON polygon offset from the road."""
    half_w = 0.00013  # ~14m in longitude at this latitude
    half_h = 0.00011  # ~12m in latitude
    cx = lon + offset_lon
    cy = lat + offset_lat
    ring = [
        [cx - half_w, cy - half_h],
        [cx + half_w, cy - half_h],
        [cx + half_w, cy + half_h],
        [cx - half_w, cy + half_h],
        [cx - half_w, cy - half_h],
    ]
    return {"type": "Polygon", "coordinates": [ring]}


def _generate_placeholder_image(frame_dir: Path, filename: str,
                                 label: str, color: tuple[int, int, int]) -> str:
    """Generate a simple colored JPEG placeholder with text overlay."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (320, 240), color)
        draw = ImageDraw.Draw(img)
        # Draw text
        try:
            font = ImageFont.truetype("arial.ttf", 16)
        except (OSError, IOError):
            font = ImageFont.load_default()
        draw.text((10, 10), label, fill=(255, 255, 255), font=font)
        draw.text((10, 200), "Demo Frame - Change Detection", fill=(200, 200, 200), font=font)

        frame_dir.mkdir(parents=True, exist_ok=True)
        filepath = frame_dir / filename
        img.save(str(filepath), "JPEG", quality=75)
        return str(Path("demo_frames") / filename)
    except ImportError:
        # Pillow not available — create a minimal JPEG manually is complex,
        # so just record the path (image won't exist on disk)
        return str(Path("demo_frames") / filename)


# ---------------------------------------------------------------------------
# Property names and typologies
# ---------------------------------------------------------------------------

DEMO_PROPERTIES = [
    ("Shop CL-001", "commercial"),
    ("Office CL-002", "commercial"),
    ("Residence CL-003", "non_commercial"),
    ("Shop CL-004", "commercial"),
    ("Residence CL-005", "non_commercial"),
    ("Shop CL-006", "commercial"),
    ("Office CL-007", "commercial"),
    ("Residence CL-008", "non_commercial"),
    ("Shop CL-009", "commercial"),
    ("Office CL-010", "commercial"),
    ("Residence CL-011", "non_commercial"),
    ("Shop CL-012", "commercial"),
    ("Residence CL-013", "non_commercial"),
    ("Shop CL-014", "commercial"),
    ("Office CL-015", "commercial"),
    ("Residence CL-016", "non_commercial"),
    ("Shop CL-017", "commercial"),
    ("Residence CL-018", "non_commercial"),
    ("Office CL-019", "commercial"),
    ("Residence CL-020", "non_commercial"),
]


@router.post("/seed", response_model=StatusResponse)
def seed_demo_data(db: Session = Depends(get_db)):
    """
    Populate the database with realistic demo data for Prayagraj Civil Lines.
    Clears all existing data first.
    """
    random.seed(42)

    # ── 1. Clear existing data ──────────────────────────────────────────────
    db.query(ChangeReport).delete()
    db.query(Prediction).delete()
    db.query(VideoFrame).delete()
    db.query(Property).delete()
    db.commit()

    # ── 2. Load route and sample 20 points ──────────────────────────────────
    all_coords = _load_route_coords()
    sampled = _sample_evenly(all_coords, 20)

    # ── 3. Create 20 property polygons ──────────────────────────────────────
    created_properties: list[Property] = []
    for i, ((lon, lat), (name, typology)) in enumerate(zip(sampled, DEMO_PROPERTIES)):
        # Alternate offset side of road
        sign = 1 if i % 2 == 0 else -1
        polygon_geojson = json.dumps(
            _make_rect_polygon(lon, lat, offset_lon=sign * 0.00015, offset_lat=sign * 0.00008)
        )
        # Centroid of the offset rectangle
        centroid_lon = lon + sign * 0.00015
        centroid_lat = lat + sign * 0.00008

        prop = Property(
            kml_id=f"CL-{i+1:03d}",
            name=name,
            existing_typology=typology,
            polygon_geojson=polygon_geojson,
            centroid_lat=centroid_lat,
            centroid_lon=centroid_lon,
            source_file="demo_seed",
        )
        db.add(prop)
        created_properties.append(prop)

    db.flush()  # get IDs assigned

    # ── 4. Create video frames (3-5 per property) ──────────────────────────
    frame_output_dir = FRAMES_DIR / "demo_frames"
    frame_output_dir.mkdir(parents=True, exist_ok=True)

    all_frames: list[VideoFrame] = []
    frame_counter = 0

    for prop in created_properties:
        n_frames = random.randint(3, 5)
        for j in range(n_frames):
            frame_counter += 1
            # GPS near property centroid with slight jitter
            jitter_lat = random.uniform(-0.00005, 0.00005)
            jitter_lon = random.uniform(-0.00005, 0.00005)

            filename = f"demo_frame_{frame_counter:04d}.jpg"
            typology_label = prop.existing_typology or "unknown"
            color = (180, 60, 60) if typology_label == "commercial" else (60, 60, 180)
            frame_path = _generate_placeholder_image(
                frame_output_dir, filename,
                f"Frame #{frame_counter} - {prop.name}\n{typology_label.title()}",
                color,
            )

            frame = VideoFrame(
                video_filename="demo_survey.mp4",
                frame_number=frame_counter,
                timestamp_sec=round(frame_counter * 1.0, 1),
                frame_path=frame_path,
                gps_lat=prop.centroid_lat + jitter_lat,
                gps_lon=prop.centroid_lon + jitter_lon,
                gps_source="demo_generated",
                matched_property_id=prop.id,
            )
            db.add(frame)
            all_frames.append(frame)

    db.flush()

    # ── 5. Create predictions (1 per frame) ─────────────────────────────────
    # Define which properties will have mismatches (indices 0-9 → first 10)
    # Properties 0-4: mismatch (predicted differs from existing)
    # Properties 5-9: mismatch
    # Properties 10-19: match (predicted same as existing)
    mismatch_property_ids = {p.id for p in created_properties[:10]}

    for frame in all_frames:
        is_mismatch = frame.matched_property_id in mismatch_property_ids
        prop = next(p for p in created_properties if p.id == frame.matched_property_id)

        if is_mismatch:
            # Predict the opposite class
            predicted = "non_commercial" if prop.existing_typology == "commercial" else "commercial"
            confidence = round(random.uniform(0.70, 0.95), 4)
        else:
            # Predict same as existing
            predicted = prop.existing_typology
            confidence = round(random.uniform(0.75, 0.95), 4)

        pred = Prediction(
            frame_id=frame.id,
            model_name="demo_yolo_v8.pt",
            predicted_class=predicted,
            confidence=confidence,
            raw_output=json.dumps({
                "type": "classification",
                "class": predicted,
                "demo": True,
            }),
        )
        db.add(pred)

    db.flush()

    # ── 6. Create change reports for all 20 properties ──────────────────────
    # Distribution:
    #   Properties 0-7   (8): flagged (mismatch, pending review)
    #   Properties 8-11  (4): approved (mismatch, reviewed)
    #   Properties 12-14 (3): rejected (mismatch, reviewed)
    #   Properties 15-19 (5): confirmed (no mismatch, match)
    status_assignments = (
        ["flagged"] * 8
        + ["approved"] * 4
        + ["rejected"] * 3
        + ["confirmed"] * 5
    )

    for idx, prop in enumerate(created_properties):
        status = status_assignments[idx]
        is_mismatch = prop.id in mismatch_property_ids

        if is_mismatch:
            predicted = "non_commercial" if prop.existing_typology == "commercial" else "commercial"
        else:
            predicted = prop.existing_typology

        # Count frames for this property
        prop_frames = [f for f in all_frames if f.matched_property_id == prop.id]
        n_frames = len(prop_frames)

        report = ChangeReport(
            property_id=prop.id,
            existing_typology=prop.existing_typology,
            predicted_typology=predicted,
            aggregated_confidence=round(random.uniform(0.70, 0.93), 4),
            num_frames_analyzed=n_frames,
            num_frames_agreeing=n_frames - random.randint(0, 1),
            status=status,
            reviewed_by="demo_reviewer" if status in ("approved", "rejected") else None,
            review_notes="Demo review" if status in ("approved", "rejected") else None,
        )
        db.add(report)

    db.commit()

    return StatusResponse(
        status="success",
        message=f"Demo data seeded: {len(created_properties)} properties, "
                f"{len(all_frames)} frames, {len(all_frames)} predictions, "
                f"20 change reports",
        detail={
            "properties": len(created_properties),
            "frames": len(all_frames),
            "predictions": len(all_frames),
            "change_reports": 20,
            "flagged": 8,
            "approved": 4,
            "rejected": 3,
            "confirmed": 5,
        },
    )
