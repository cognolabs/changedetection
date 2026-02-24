"""YOLO inference wrapper for property classification."""

import json
from pathlib import Path
from typing import Optional

from backend.config import MODELS_DIR, FRAMES_DIR


def get_available_models() -> list[str]:
    """List available YOLO model files."""
    return [f.name for f in MODELS_DIR.glob("*.pt")]


def run_inference(
    model_name: str,
    frame_paths: list[str],
    confidence_threshold: float = 0.25,
) -> list[dict]:
    """
    Run YOLO inference on a list of frame images.

    Args:
        model_name: Name of .pt model file in models directory
        frame_paths: List of frame paths relative to FRAMES_DIR
        confidence_threshold: Minimum confidence for predictions

    Returns:
        List of dicts: {frame_path, predicted_class, confidence, raw_output}
    """
    from ultralytics import YOLO

    model_path = MODELS_DIR / model_name
    if not model_path.exists():
        raise FileNotFoundError(f"Model not found: {model_path}")

    model = YOLO(str(model_path))

    results = []
    for rel_path in frame_paths:
        full_path = FRAMES_DIR / rel_path
        if not full_path.exists():
            continue

        preds = model(str(full_path), verbose=False)

        if not preds:
            continue

        pred = preds[0]

        # Handle classification model output
        if hasattr(pred, "probs") and pred.probs is not None:
            probs = pred.probs
            top_class_idx = probs.top1
            top_conf = float(probs.top1conf)
            class_name = pred.names[top_class_idx]

            results.append({
                "frame_path": rel_path,
                "predicted_class": _normalize_class(class_name),
                "confidence": round(top_conf, 4),
                "raw_output": json.dumps({
                    "type": "classification",
                    "class": class_name,
                    "all_probs": {
                        pred.names[i]: round(float(probs.data[i]), 4)
                        for i in range(len(probs.data))
                    },
                }),
            })

        # Handle detection model output
        elif hasattr(pred, "boxes") and pred.boxes is not None and len(pred.boxes) > 0:
            # Use the highest-confidence detection
            boxes = pred.boxes
            best_idx = boxes.conf.argmax()
            best_conf = float(boxes.conf[best_idx])
            best_cls = int(boxes.cls[best_idx])
            class_name = pred.names[best_cls]

            if best_conf >= confidence_threshold:
                results.append({
                    "frame_path": rel_path,
                    "predicted_class": _normalize_class(class_name),
                    "confidence": round(best_conf, 4),
                    "raw_output": json.dumps({
                        "type": "detection",
                        "class": class_name,
                        "num_detections": len(boxes),
                        "best_box": boxes.xyxy[best_idx].tolist(),
                    }),
                })

    return results


def _normalize_class(class_name: str) -> str:
    """Normalize YOLO class name to standard typology."""
    name = class_name.lower().strip()
    if name in ("commercial", "com", "c", "shop", "store", "business"):
        return "commercial"
    elif name in ("non_commercial", "non-commercial", "residential", "res", "nc", "house", "home"):
        return "non_commercial"
    elif name in ("mix", "mixed"):
        return "mix"
    return name
