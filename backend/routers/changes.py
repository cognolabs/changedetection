"""Changes router — change detection, review workflow, export."""

import csv
import io
import json
import logging
from collections import defaultdict

from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from backend.database import get_db
from backend.models import Property, VideoFrame, Prediction, ChangeReport
from backend.schemas import ChangeReportOut, ReviewRequest, ChangeSummary, StatusResponse
from backend.services.change_engine import detect_changes

router = APIRouter()


@router.post("/detect", response_model=StatusResponse)
def run_change_detection(db: Session = Depends(get_db)):
    """Run mismatch detection: compare predictions against existing typology."""
    # Clear existing reports
    db.query(ChangeReport).delete()

    # Build property -> predictions mapping
    properties = db.query(Property).all()
    if not properties:
        return StatusResponse(status="info", message="No properties in database")

    total_preds = db.query(Prediction).count()
    total_frames_with_property = (
        db.query(VideoFrame)
        .filter(VideoFrame.matched_property_id.isnot(None))
        .count()
    )
    total_frames_with_gps = (
        db.query(VideoFrame)
        .filter(VideoFrame.gps_lat.isnot(None))
        .count()
    )
    logger.info(
        "Change detection: %d properties, %d predictions total, "
        "%d frames with GPS, %d frames matched to properties",
        len(properties), total_preds, total_frames_with_gps, total_frames_with_property,
    )

    props_with_preds = []
    props_with_data = 0
    for prop in properties:
        # Get all predictions for frames matched to this property
        preds = (
            db.query(Prediction)
            .join(VideoFrame, Prediction.frame_id == VideoFrame.id)
            .filter(VideoFrame.matched_property_id == prop.id)
            .all()
        )

        if preds:
            props_with_data += 1

        props_with_preds.append({
            "property_id": prop.id,
            "existing_typology": prop.existing_typology,
            "predictions": [
                {"predicted_class": p.predicted_class, "confidence": p.confidence}
                for p in preds
            ],
        })

    logger.info("Properties with prediction data: %d/%d", props_with_data, len(properties))

    # Run change detection engine
    reports = detect_changes(props_with_preds)

    # Save reports
    flagged_count = 0
    for report_data in reports:
        report = ChangeReport(**report_data)
        db.add(report)
        if report_data["status"] == "flagged":
            flagged_count += 1

    db.commit()

    return StatusResponse(
        status="success",
        message=f"Change detection complete: {flagged_count} mismatches flagged out of {len(reports)} analyzed",
        detail={
            "total_analyzed": len(reports),
            "flagged": flagged_count,
            "confirmed": len(reports) - flagged_count,
        },
    )


@router.get("", response_model=list[ChangeReportOut])
def list_changes(
    status: str | None = Query(None, description="Filter by status: flagged/approved/rejected"),
    db: Session = Depends(get_db),
):
    """List change reports with optional status filter."""
    query = db.query(ChangeReport)
    if status:
        query = query.filter(ChangeReport.status == status)
    return query.order_by(ChangeReport.aggregated_confidence.desc()).all()


@router.get("/summary", response_model=ChangeSummary)
def get_summary(db: Session = Depends(get_db)):
    """Get aggregate statistics about change detection results."""
    total_properties = db.query(Property).count()
    reports = db.query(ChangeReport).all()

    return ChangeSummary(
        total_properties=total_properties,
        properties_analyzed=len(reports),
        total_flagged=sum(1 for r in reports if r.status == "flagged"),
        total_approved=sum(1 for r in reports if r.status == "approved"),
        total_rejected=sum(1 for r in reports if r.status == "rejected"),
    )


@router.get("/export/csv")
def export_csv(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Export change reports as CSV."""
    query = db.query(ChangeReport).join(Property)
    if status:
        query = query.filter(ChangeReport.status == status)

    reports = query.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "property_id", "property_name", "existing_typology",
        "predicted_typology", "confidence", "frames_analyzed",
        "frames_agreeing", "status", "reviewed_by", "notes",
    ])

    for r in reports:
        prop = db.query(Property).filter(Property.id == r.property_id).first()
        writer.writerow([
            r.property_id,
            prop.name if prop else "",
            r.existing_typology,
            r.predicted_typology,
            r.aggregated_confidence,
            r.num_frames_analyzed,
            r.num_frames_agreeing,
            r.status,
            r.reviewed_by or "",
            r.review_notes or "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=change_reports.csv"},
    )


@router.get("/export/geojson")
def export_geojson(
    status: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Export change reports as GeoJSON with updated typology."""
    query = db.query(ChangeReport).join(Property)
    if status:
        query = query.filter(ChangeReport.status == status)

    reports = query.all()
    features = []

    for r in reports:
        prop = db.query(Property).filter(Property.id == r.property_id).first()
        if not prop:
            continue

        features.append({
            "type": "Feature",
            "geometry": json.loads(prop.polygon_geojson),
            "properties": {
                "id": prop.id,
                "name": prop.name,
                "existing_typology": r.existing_typology,
                "predicted_typology": r.predicted_typology,
                "aggregated_confidence": r.aggregated_confidence,
                "status": r.status,
                "reviewed_by": r.reviewed_by,
                "review_notes": r.review_notes,
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/{change_id}", response_model=ChangeReportOut)
def get_change(change_id: int, db: Session = Depends(get_db)):
    """Get a single change report."""
    report = db.query(ChangeReport).filter(ChangeReport.id == change_id).first()
    if not report:
        raise HTTPException(404, "Change report not found")
    return report


@router.patch("/{change_id}/review", response_model=ChangeReportOut)
def review_change(
    change_id: int,
    review: ReviewRequest,
    db: Session = Depends(get_db),
):
    """Approve or reject a flagged change."""
    report = db.query(ChangeReport).filter(ChangeReport.id == change_id).first()
    if not report:
        raise HTTPException(404, "Change report not found")

    if review.status not in ("approved", "rejected"):
        raise HTTPException(400, "Status must be 'approved' or 'rejected'")

    report.status = review.status
    report.reviewed_by = review.reviewed_by
    report.review_notes = review.review_notes
    db.commit()
    db.refresh(report)

    return report
