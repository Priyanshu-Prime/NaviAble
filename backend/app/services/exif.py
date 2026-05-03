"""Extract GPS coordinates from image EXIF, if present."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional, Tuple

from PIL import Image, ExifTags

log = logging.getLogger(__name__)

_GPSINFO_TAG = next(k for k, v in ExifTags.TAGS.items() if v == "GPSInfo")


def _to_decimal(dms: tuple, ref: str) -> float:
    deg, minutes, seconds = (float(x) for x in dms)
    val = deg + minutes / 60.0 + seconds / 3600.0
    if ref in ("S", "W"):
        val = -val
    return val


def extract_gps(image_path: Path) -> Optional[Tuple[float, float]]:
    """Return (lat, lon) from EXIF, or None if missing/invalid."""
    try:
        with Image.open(image_path) as img:
            exif = img._getexif() or {}
    except Exception as exc:
        log.warning("exif.read_failed path=%s err=%s", image_path, exc)
        return None

    gps = exif.get(_GPSINFO_TAG)
    if not gps:
        return None

    gps_tags = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}
    try:
        lat = _to_decimal(gps_tags["GPSLatitude"], gps_tags["GPSLatitudeRef"])
        lon = _to_decimal(gps_tags["GPSLongitude"], gps_tags["GPSLongitudeRef"])
    except (KeyError, ValueError, TypeError) as exc:
        log.info("exif.parse_failed path=%s err=%s", image_path, exc)
        return None

    if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
        return None
    return lat, lon
