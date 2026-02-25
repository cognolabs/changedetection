"""Shapefile parsing service — extracts property polygons from ward-based shapefiles."""

import json
import zipfile
import tempfile
from pathlib import Path

import shapefile  # pyshp

from backend.utils.geometry_utils import polygon_to_geojson, get_centroid
from backend.services.kml_parser import normalize_typology

from shapely.geometry import shape as shapely_shape, Polygon


def parse_shapefile_zip(zip_path: Path) -> list[dict]:
    """
    Extract a ZIP containing ward-based shapefiles, parse plot (polygon) and
    survey (point) files, join by parcel ID, and return enriched property dicts.

    Returns same format as kml_parser: list of dicts with keys:
      kml_id, name, existing_typology, polygon_geojson,
      centroid_lat, centroid_lon, source_file, extra_attributes
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        with zipfile.ZipFile(zip_path, "r") as zf:
            zf.extractall(tmp)

        # Find all .shp files recursively
        shp_files = list(tmp.rglob("*.shp"))
        if not shp_files:
            raise ValueError("No .shp files found in ZIP archive")

        # Separate into plot (polygon) and survey (point) shapefiles
        plot_files = []
        survey_files = []
        for shp_path in shp_files:
            try:
                sf = shapefile.Reader(str(shp_path), encoding="utf-8", encodingErrors="replace")
                shape_type = sf.shapeType
                sf.close()
                # shapefile types: 5=Polygon, 1=Point, 11=PointZ, 15=PolygonZ
                if shape_type in (shapefile.POLYGON, shapefile.POLYGONZ, shapefile.POLYGONM):
                    plot_files.append(shp_path)
                elif shape_type in (shapefile.POINT, shapefile.POINTZ, shapefile.POINTM):
                    survey_files.append(shp_path)
            except Exception:
                continue

        if not plot_files:
            raise ValueError("No polygon shapefiles found in ZIP archive")

        # Parse all survey files into a combined lookup by parcel ID
        survey_lookup: dict[str, dict] = {}
        for sf_path in survey_files:
            survey_lookup.update(parse_survey_shapefile(sf_path))

        # Parse all plot files and join with survey data
        properties = []
        for pf_path in plot_files:
            plots = parse_plot_shapefile(pf_path)
            for plot in plots:
                parcel_id = plot.get("parcel_id", "")
                # Join survey data if available
                if parcel_id and parcel_id in survey_lookup:
                    survey_data = survey_lookup[parcel_id]
                    # Merge survey attributes into extra_attributes
                    extra = json.loads(plot.get("extra_attributes") or "{}")
                    extra["survey_data"] = survey_data
                    plot["extra_attributes"] = json.dumps(extra, ensure_ascii=False, default=str)

                properties.append(plot)

        return properties


def parse_plot_shapefile(shp_path: Path) -> list[dict]:
    """
    Parse a single polygon shapefile and return property dicts.
    Expects attributes like Category, Owner, parcelId, etc.
    """
    sf = shapefile.Reader(str(shp_path), encoding="utf-8", encodingErrors="replace")
    field_names = [f[0] for f in sf.fields[1:]]  # skip DeletionFlag
    properties = []

    for sr in sf.shapeRecords():
        geom = sr.shape
        rec = sr.record

        # Build attribute dict from record
        attrs = {}
        for i, fname in enumerate(field_names):
            val = rec[i]
            if isinstance(val, bytes):
                val = val.decode("utf-8", errors="replace")
            if val is not None:
                attrs[fname] = val

        # Convert pyshp geometry to shapely
        try:
            geojson_geom = geom.__geo_interface__
            polygon = shapely_shape(geojson_geom)
        except Exception:
            continue

        # Ensure it's a Polygon
        if not isinstance(polygon, Polygon):
            if hasattr(polygon, 'geoms'):
                # MultiPolygon — take the largest
                polygon = max(polygon.geoms, key=lambda p: p.area)
            else:
                continue

        if not polygon.is_valid or polygon.is_empty:
            continue

        # Extract parcel ID (try common field names)
        parcel_id = None
        for key in ("parcelId", "PARCEL_ID", "parcel_id", "ParcelId", "PARCELID", "parcelid"):
            if key in attrs:
                parcel_id = str(attrs[key]).strip()
                break

        # Extract typology from Category field
        typology_raw = None
        for key in ("Category", "CATEGORY", "category", "typology", "Typology", "TYPE", "type", "land_use", "LandUse"):
            if key in attrs:
                typology_raw = str(attrs[key]).strip()
                break

        # Extract name
        name = None
        for key in ("Name", "NAME", "name", "Owner", "OWNER", "owner"):
            if key in attrs:
                val = attrs[key]
                if val and str(val).strip():
                    name = str(val).strip()
                    break

        centroid_lat, centroid_lon = get_centroid(polygon)

        properties.append({
            "kml_id": parcel_id,
            "name": name,
            "existing_typology": normalize_typology(typology_raw),
            "polygon_geojson": polygon_to_geojson(polygon),
            "centroid_lat": centroid_lat,
            "centroid_lon": centroid_lon,
            "source_file": shp_path.name,
            "extra_attributes": json.dumps(attrs, ensure_ascii=False, default=str) if attrs else None,
            "parcel_id": parcel_id,  # keep for join, not stored in DB
        })

    sf.close()
    return properties


def parse_survey_shapefile(shp_path: Path) -> dict[str, dict]:
    """
    Parse a point shapefile containing survey data.
    Returns dict keyed by parcel_id with all survey attributes.
    """
    sf = shapefile.Reader(str(shp_path), encoding="utf-8", encodingErrors="replace")
    field_names = [f[0] for f in sf.fields[1:]]
    result: dict[str, dict] = {}

    for sr in sf.shapeRecords():
        rec = sr.record

        attrs = {}
        for i, fname in enumerate(field_names):
            val = rec[i]
            if isinstance(val, bytes):
                val = val.decode("utf-8", errors="replace")
            if val is not None:
                attrs[fname] = val

        # Find parcel ID
        parcel_id = None
        for key in ("PARCEL_ID", "parcelId", "parcel_id", "ParcelId", "PARCELID", "parcelid"):
            if key in attrs:
                parcel_id = str(attrs[key]).strip()
                break

        if parcel_id:
            result[parcel_id] = attrs

    sf.close()
    return result
