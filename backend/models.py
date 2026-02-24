from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import relationship
import enum

from backend.database import Base


class TypologyEnum(str, enum.Enum):
    commercial = "commercial"
    non_commercial = "non_commercial"
    mix = "mix"


class ChangeStatus(str, enum.Enum):
    flagged = "flagged"
    approved = "approved"
    rejected = "rejected"


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True, index=True)
    kml_id = Column(String, nullable=True)
    name = Column(String, nullable=True)
    existing_typology = Column(String, nullable=True)
    polygon_geojson = Column(Text, nullable=False)
    centroid_lat = Column(Float, nullable=False)
    centroid_lon = Column(Float, nullable=False)
    source_file = Column(String, nullable=True)
    extra_attributes = Column(Text, nullable=True)  # JSON string

    frames = relationship("VideoFrame", back_populates="property")
    change_reports = relationship("ChangeReport", back_populates="property")


class VideoFrame(Base):
    __tablename__ = "video_frames"

    id = Column(Integer, primary_key=True, index=True)
    video_filename = Column(String, nullable=False)
    frame_number = Column(Integer, nullable=False)
    timestamp_sec = Column(Float, nullable=False)
    frame_path = Column(String, nullable=False)
    gps_lat = Column(Float, nullable=True)
    gps_lon = Column(Float, nullable=True)
    gps_source = Column(String, nullable=True)
    matched_property_id = Column(Integer, ForeignKey("properties.id"), nullable=True)

    property = relationship("Property", back_populates="frames")
    predictions = relationship("Prediction", back_populates="frame")


class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    frame_id = Column(Integer, ForeignKey("video_frames.id"), nullable=False)
    model_name = Column(String, nullable=False)
    predicted_class = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    raw_output = Column(Text, nullable=True)  # JSON string

    frame = relationship("VideoFrame", back_populates="predictions")


class ChangeReport(Base):
    __tablename__ = "change_reports"

    id = Column(Integer, primary_key=True, index=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False)
    existing_typology = Column(String, nullable=True)
    predicted_typology = Column(String, nullable=True)
    aggregated_confidence = Column(Float, nullable=True)
    num_frames_analyzed = Column(Integer, default=0)
    num_frames_agreeing = Column(Integer, default=0)
    status = Column(String, default=ChangeStatus.flagged.value)
    reviewed_by = Column(String, nullable=True)
    review_notes = Column(Text, nullable=True)

    property = relationship("Property", back_populates="change_reports")
