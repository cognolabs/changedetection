"""Change detection engine — aggregates predictions and flags mismatches."""

from collections import Counter
from typing import Optional

from backend.config import CONFIDENCE_THRESHOLD, MIN_FRAMES_FOR_PREDICTION


def aggregate_predictions(
    predictions: list[dict],
) -> Optional[dict]:
    """
    Aggregate multiple frame predictions for a single property using
    confidence-weighted majority voting.

    Args:
        predictions: List of dicts with 'predicted_class' and 'confidence'

    Returns:
        Dict with aggregated_class, aggregated_confidence,
        num_frames_analyzed, num_frames_agreeing
        or None if insufficient data
    """
    if len(predictions) < MIN_FRAMES_FOR_PREDICTION:
        return None

    # Weighted vote: sum confidence per class
    class_scores: dict[str, float] = {}
    class_counts: dict[str, int] = Counter()

    for pred in predictions:
        cls = pred["predicted_class"]
        conf = pred["confidence"]
        class_scores[cls] = class_scores.get(cls, 0.0) + conf
        class_counts[cls] += 1

    # Winner is the class with highest total weighted score
    winner = max(class_scores, key=class_scores.get)
    total_confidence = sum(class_scores.values())
    winner_confidence = class_scores[winner] / total_confidence if total_confidence > 0 else 0

    return {
        "predicted_typology": winner,
        "aggregated_confidence": round(winner_confidence, 4),
        "num_frames_analyzed": len(predictions),
        "num_frames_agreeing": class_counts[winner],
    }


def detect_changes(
    properties_with_predictions: list[dict],
    confidence_threshold: float = CONFIDENCE_THRESHOLD,
) -> list[dict]:
    """
    Compare aggregated predictions against existing typology for each property.

    Args:
        properties_with_predictions: List of dicts with:
            - property_id, existing_typology
            - predictions: list of {predicted_class, confidence}
        confidence_threshold: Minimum aggregated confidence to flag

    Returns:
        List of change report dicts (only mismatches are flagged)
    """
    reports = []

    for prop in properties_with_predictions:
        agg = aggregate_predictions(prop["predictions"])
        if agg is None:
            continue

        existing = prop.get("existing_typology")
        predicted = agg["predicted_typology"]

        # Determine if this is a mismatch
        is_mismatch = (
            existing is not None
            and predicted != existing
            and agg["aggregated_confidence"] >= confidence_threshold
        )

        reports.append({
            "property_id": prop["property_id"],
            "existing_typology": existing,
            "predicted_typology": predicted,
            "aggregated_confidence": agg["aggregated_confidence"],
            "num_frames_analyzed": agg["num_frames_analyzed"],
            "num_frames_agreeing": agg["num_frames_agreeing"],
            "status": "flagged" if is_mismatch else "confirmed",
        })

    return reports
