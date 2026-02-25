"""Inference router — YOLO model upload and inference execution."""

import io
import json
import shutil
from pathlib import Path

import cv2
import numpy as np
from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import MODELS_DIR, FRAMES_DIR
from backend.models import VideoFrame, Prediction
from backend.schemas import PredictionOut, StatusResponse
from backend.services.detector import run_inference, get_available_models

router = APIRouter()


@router.post("/upload-model", response_model=StatusResponse)
async def upload_model(
    file: UploadFile = File(...),
):
    """Upload a YOLO .pt model file."""
    if not file.filename or not file.filename.endswith(".pt"):
        raise HTTPException(400, "File must be a .pt model file")

    model_path = MODELS_DIR / file.filename
    with open(model_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    return StatusResponse(
        status="success",
        message=f"Model uploaded: {file.filename}",
        detail={"file": file.filename},
    )


@router.get("/models", response_model=list[str])
def list_models():
    """List available YOLO models."""
    return get_available_models()


@router.post("/run", response_model=StatusResponse)
def run_model_inference(
    model_name: str = Query(..., description="Name of .pt model file"),
    property_id: int | None = Query(None, description="Only frames matched to this property"),
    db: Session = Depends(get_db),
):
    """Run YOLO inference on extracted frames."""
    # Verify model exists
    model_path = MODELS_DIR / model_name
    if not model_path.exists():
        raise HTTPException(404, f"Model not found: {model_name}")

    # Get frames to process
    query = db.query(VideoFrame)
    if property_id is not None:
        query = query.filter(VideoFrame.matched_property_id == property_id)

    frames = query.all()
    if not frames:
        return StatusResponse(status="info", message="No frames to process")

    # Collect frame paths
    frame_paths = [f.frame_path for f in frames]
    frame_path_to_id = {f.frame_path: f.id for f in frames}

    # Run inference
    try:
        results = run_inference(model_name, frame_paths)
    except Exception as e:
        raise HTTPException(500, f"Inference failed: {e}")

    # Save predictions
    count = 0
    for result in results:
        frame_id = frame_path_to_id.get(result["frame_path"])
        if frame_id is None:
            continue

        pred = Prediction(
            frame_id=frame_id,
            model_name=model_name,
            predicted_class=result["predicted_class"],
            confidence=result["confidence"],
            raw_output=result.get("raw_output"),
        )
        db.add(pred)
        count += 1

    db.commit()

    return StatusResponse(
        status="success",
        message=f"Generated {count} predictions from {len(frames)} frames",
        detail={"predictions": count, "frames_processed": len(frames)},
    )


@router.get("/predictions", response_model=list[PredictionOut])
def list_predictions(
    frame_id: int | None = Query(None),
    model_name: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """List predictions with optional filters."""
    query = db.query(Prediction)
    if frame_id is not None:
        query = query.filter(Prediction.frame_id == frame_id)
    if model_name:
        query = query.filter(Prediction.model_name == model_name)
    return query.all()


@router.get("/predictions/{prediction_id}/image")
def get_prediction_image(prediction_id: int, db: Session = Depends(get_db)):
    """Serve the frame image with bounding boxes and prediction label drawn on it."""
    pred = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if not pred:
        raise HTTPException(404, "Prediction not found")

    frame = db.query(VideoFrame).filter(VideoFrame.id == pred.frame_id).first()
    if not frame:
        raise HTTPException(404, "Frame not found")

    full_path = FRAMES_DIR / frame.frame_path
    if not full_path.exists():
        raise HTTPException(404, "Frame file not found on disk")

    img = cv2.imread(str(full_path))
    if img is None:
        raise HTTPException(500, "Could not read frame image")

    h, w = img.shape[:2]

    # Draw bounding box if detection model output
    raw = {}
    if pred.raw_output:
        try:
            raw = json.loads(pred.raw_output)
        except json.JSONDecodeError:
            pass

    box_color = (0, 255, 0)  # green
    label = f"{pred.predicted_class} {pred.confidence * 100:.0f}%"

    if raw.get("type") == "detection" and raw.get("best_box"):
        box = raw["best_box"]
        x1, y1, x2, y2 = int(box[0]), int(box[1]), int(box[2]), int(box[3])
        cv2.rectangle(img, (x1, y1), (x2, y2), box_color, 2)
        # Label background
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(img, (x1, y1 - th - 10), (x1 + tw + 6, y1), box_color, -1)
        cv2.putText(img, label, (x1 + 3, y1 - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 2)
    else:
        # Classification model — draw label banner at top
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)
        cv2.rectangle(img, (0, 0), (tw + 16, th + 16), box_color, -1)
        cv2.putText(img, label, (8, th + 8), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 0, 0), 2)

    _, buf = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 90])
    return StreamingResponse(io.BytesIO(buf.tobytes()), media_type="image/jpeg")
