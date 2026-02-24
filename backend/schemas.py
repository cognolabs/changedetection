from pydantic import BaseModel
from typing import Optional


# --- Property Schemas ---

class PropertyOut(BaseModel):
    id: int
    kml_id: Optional[str] = None
    name: Optional[str] = None
    existing_typology: Optional[str] = None
    centroid_lat: float
    centroid_lon: float
    source_file: Optional[str] = None

    model_config = {"from_attributes": True}


class PropertyDetail(PropertyOut):
    polygon_geojson: str
    extra_attributes: Optional[str] = None


# --- Video Frame Schemas ---

class VideoFrameOut(BaseModel):
    id: int
    video_filename: str
    frame_number: int
    timestamp_sec: float
    frame_path: str
    gps_lat: Optional[float] = None
    gps_lon: Optional[float] = None
    gps_source: Optional[str] = None
    matched_property_id: Optional[int] = None

    model_config = {"from_attributes": True}


# --- Prediction Schemas ---

class PredictionOut(BaseModel):
    id: int
    frame_id: int
    model_name: str
    predicted_class: str
    confidence: float
    raw_output: Optional[str] = None

    model_config = {"from_attributes": True}


# --- Change Report Schemas ---

class ChangeReportOut(BaseModel):
    id: int
    property_id: int
    existing_typology: Optional[str] = None
    predicted_typology: Optional[str] = None
    aggregated_confidence: Optional[float] = None
    num_frames_analyzed: int = 0
    num_frames_agreeing: int = 0
    status: str = "flagged"
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ReviewRequest(BaseModel):
    status: str  # "approved" or "rejected"
    reviewed_by: Optional[str] = None
    review_notes: Optional[str] = None


class ChangeSummary(BaseModel):
    total_properties: int
    properties_analyzed: int
    total_flagged: int
    total_approved: int
    total_rejected: int


# --- Generic ---

class StatusResponse(BaseModel):
    status: str
    message: str
    detail: Optional[dict] = None
