"""Properties router — property upload (Shapefile/KML), CRUD, GeoJSON export."""

import json
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, UploadFile, File, Query, HTTPException
from sqlalchemy.orm import Session

from backend.database import get_db
from backend.config import UPLOAD_DIR
from backend.models import Property
from backend.schemas import PropertyOut, PropertyDetail, StatusResponse
from backend.services.kml_parser import parse_file
from backend.services.shapefile_parser import parse_shapefile_zip

router = APIRouter()


@router.post("/upload", response_model=StatusResponse)
async def upload_properties(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload a Shapefile ZIP, KML, or KMZ file and import property polygons."""
    if not file.filename:
        raise HTTPException(400, "No filename provided")

    suffix = Path(file.filename).suffix.lower()
    if suffix not in (".kml", ".kmz", ".zip"):
        raise HTTPException(400, "File must be .kml, .kmz, or .zip (shapefile)")

    # Save uploaded file
    upload_path = UPLOAD_DIR / file.filename
    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    # Parse and import
    try:
        if suffix == ".zip":
            properties = parse_shapefile_zip(upload_path)
            # Remove the internal 'parcel_id' key used for joining (not a DB column)
            for p in properties:
                p.pop("parcel_id", None)
        else:
            properties = parse_file(upload_path)
    except Exception as e:
        raise HTTPException(400, f"Failed to parse file: {e}")

    if not properties:
        raise HTTPException(400, "No valid property polygons found in file")

    # Insert into database
    count = 0
    for prop_data in properties:
        prop = Property(**prop_data)
        db.add(prop)
        count += 1

    db.commit()

    return StatusResponse(
        status="success",
        message=f"Imported {count} properties from {file.filename}",
        detail={"count": count, "file": file.filename},
    )


@router.get("", response_model=list[PropertyOut])
def list_properties(
    typology: str | None = Query(None, description="Filter by typology"),
    db: Session = Depends(get_db),
):
    """List all properties, optionally filtered by typology."""
    query = db.query(Property)
    if typology:
        query = query.filter(Property.existing_typology == typology)
    return query.all()


@router.get("/geojson", response_model=None)
def get_geojson(
    typology: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """Export properties as a GeoJSON FeatureCollection for map display."""
    query = db.query(Property)
    if typology:
        query = query.filter(Property.existing_typology == typology)

    features = []
    for prop in query.all():
        feature = {
            "type": "Feature",
            "geometry": json.loads(prop.polygon_geojson),
            "properties": {
                "id": prop.id,
                "name": prop.name,
                "kml_id": prop.kml_id,
                "existing_typology": prop.existing_typology,
                "centroid_lat": prop.centroid_lat,
                "centroid_lon": prop.centroid_lon,
            },
        }
        features.append(feature)

    return {
        "type": "FeatureCollection",
        "features": features,
    }


@router.get("/{property_id}", response_model=PropertyDetail)
def get_property(property_id: int, db: Session = Depends(get_db)):
    """Get a single property with full details."""
    prop = db.query(Property).filter(Property.id == property_id).first()
    if not prop:
        raise HTTPException(404, "Property not found")
    return prop
