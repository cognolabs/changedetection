"""KML/KMZ parsing service — extracts property polygons from GIS files."""

import json
import zipfile
import tempfile
from pathlib import Path
from typing import Optional

from lxml import etree
from shapely.geometry import Polygon

from backend.utils.geometry_utils import coords_to_polygon, polygon_to_geojson, get_centroid

# KML namespace
KML_NS = "{http://www.opengis.net/kml/2.2}"

# Typology normalization map
TYPOLOGY_MAP = {
    "c": "commercial",
    "com": "commercial",
    "commercial": "commercial",
    "comm": "commercial",
    "nc": "non_commercial",
    "non_commercial": "non_commercial",
    "non-commercial": "non_commercial",
    "noncommercial": "non_commercial",
    "residential": "non_commercial",
    "res": "non_commercial",
    "r": "non_commercial",
    "non residential": "commercial",
    "nonresidential": "commercial",
    "mix": "mix",
    "mixed": "mix",
}


def normalize_typology(value: Optional[str]) -> Optional[str]:
    """Normalize typology value to 'commercial', 'non_commercial', or 'mix'."""
    if not value:
        return None
    return TYPOLOGY_MAP.get(value.strip().lower())


def parse_kml_bytes(kml_bytes: bytes, source_filename: str) -> list[dict]:
    """
    Parse KML XML bytes and extract property placemarks.
    Returns list of dicts with keys:
      kml_id, name, existing_typology, polygon_geojson,
      centroid_lat, centroid_lon, source_file, extra_attributes
    """
    root = etree.fromstring(kml_bytes)
    placemarks = root.findall(f".//{KML_NS}Placemark")
    properties = []

    for pm in placemarks:
        # Extract polygon coordinates
        coord_el = pm.find(f".//{KML_NS}coordinates")
        if coord_el is None or not coord_el.text:
            continue

        try:
            polygon = coords_to_polygon(coord_el.text)
        except (ValueError, IndexError):
            continue

        if not polygon.is_valid or polygon.is_empty:
            continue

        # Name
        name_el = pm.find(f"{KML_NS}name")
        name = name_el.text.strip() if name_el is not None and name_el.text else None

        # ID
        kml_id = pm.get("id")

        # ExtendedData
        extra = {}
        typology_raw = None
        extended = pm.find(f"{KML_NS}ExtendedData")
        if extended is not None:
            for data in extended.findall(f"{KML_NS}Data"):
                data_name = data.get("name", "")
                value_el = data.find(f"{KML_NS}value")
                value = value_el.text.strip() if value_el is not None and value_el.text else ""
                extra[data_name] = value
                if data_name.lower() in ("typology", "type", "uso", "land_use", "landuse", "category"):
                    typology_raw = value

            # Also check SimpleData in SchemaData
            for sd in extended.findall(f".//{KML_NS}SimpleData"):
                sd_name = sd.get("name", "")
                sd_value = sd.text.strip() if sd.text else ""
                extra[sd_name] = sd_value
                if sd_name.lower() in ("typology", "type", "uso", "land_use", "landuse", "category"):
                    typology_raw = sd_value

        # Also search in description for typology hints
        desc_el = pm.find(f"{KML_NS}description")
        if desc_el is not None and desc_el.text and not typology_raw:
            extra["description"] = desc_el.text.strip()

        centroid_lat, centroid_lon = get_centroid(polygon)

        properties.append({
            "kml_id": kml_id,
            "name": name,
            "existing_typology": normalize_typology(typology_raw),
            "polygon_geojson": polygon_to_geojson(polygon),
            "centroid_lat": centroid_lat,
            "centroid_lon": centroid_lon,
            "source_file": source_filename,
            "extra_attributes": json.dumps(extra, ensure_ascii=False, default=str) if extra else None,
        })

    return properties


def parse_file(file_path: Path) -> list[dict]:
    """Parse a KML or KMZ file and return property dicts."""
    suffix = file_path.suffix.lower()

    if suffix == ".kmz":
        with zipfile.ZipFile(file_path, "r") as zf:
            kml_names = [n for n in zf.namelist() if n.lower().endswith(".kml")]
            if not kml_names:
                raise ValueError("No KML file found inside KMZ archive")
            kml_bytes = zf.read(kml_names[0])
    elif suffix == ".kml":
        kml_bytes = file_path.read_bytes()
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

    return parse_kml_bytes(kml_bytes, file_path.name)
