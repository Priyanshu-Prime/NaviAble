"""Export ramp shapefile data for downstream use.

This utility reads the GIS ramp layer in `Ramps_v2/Sidewalk_Ramps_2010/`
and exports:
  - a GeoJSON file with the raw polygon geometries and attributes
  - a CSV file with per-feature bounding boxes
  - a short console summary for quick inspection

Important: this does NOT directly train YOLO. It gives you the ramp polygons
so you can:
  1) visualize them,
  2) overlay them on imagery, and
  3) convert them to image labels if you have matching raster images.

Requirements:
  pip install pyshp

Example:
  python yolo/export_ramp_shapefile.py \
    --shp /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/Ramps_v2/Sidewalk_Ramps_2010/Sidewalk_Ramps_2010.shp \
    --out-dir /Users/vedantsunillande/spot-repo/NaviAble/NaviAble/ramp_exports
"""
from __future__ import annotations

import argparse
import csv
import json
import os
from pathlib import Path
from typing import Any, Dict, List

try:
    import shapefile  # type: ignore
except ModuleNotFoundError as exc:  # pragma: no cover - handled at runtime
    raise SystemExit(
        "Missing dependency: pyshp. Install it with `pip install pyshp`."
    ) from exc


DEFAULT_SHP = Path(
    "/Users/vedantsunillande/spot-repo/NaviAble/NaviAble/Ramps_v2/Sidewalk_Ramps_2010/Sidewalk_Ramps_2010.shp"
)
DEFAULT_OUT_DIR = Path(
    "/Users/vedantsunillande/spot-repo/NaviAble/NaviAble/ramp_exports"
)


def safe_name(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def json_safe(value: Any) -> Any:
    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            return str(value)
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def feature_properties(field_names: List[str], record: Any) -> Dict[str, Any]:
    props: Dict[str, Any] = {}
    for idx, field_name in enumerate(field_names):
        props[field_name] = json_safe(record[idx] if idx < len(record) else None)
    return props


def shape_bbox(shape: Any) -> List[float]:
    if getattr(shape, "bbox", None):
        return list(shape.bbox)

    pts = getattr(shape, "points", None) or []
    if not pts:
        return [0.0, 0.0, 0.0, 0.0]

    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return [min(xs), min(ys), max(xs), max(ys)]


def export_shapefile(shp_path: Path, out_dir: Path, prefix: str, class_name: str, class_id: int) -> Dict[str, Any]:
    reader = shapefile.Reader(str(shp_path))
    out_dir.mkdir(parents=True, exist_ok=True)

    field_names = [f[0] for f in reader.fields[1:]]
    shapes = reader.shapes()
    records = reader.records()

    if len(shapes) != len(records):
        raise RuntimeError(f"Shape/record mismatch: {len(shapes)} shapes vs {len(records)} records")

    features: List[Dict[str, Any]] = []
    bbox_rows: List[Dict[str, Any]] = []
    geom_types: Dict[str, int] = {}

    for idx, (shape, record) in enumerate(zip(shapes, records), start=1):
        geo = shape.__geo_interface__
        geom_type = geo.get("type", "Unknown")
        geom_types[geom_type] = geom_types.get(geom_type, 0) + 1

        props = feature_properties(field_names, record)
        props.update({
            "feature_id": idx,
            "source_shapefile": shp_path.name,
            "class_name": class_name,
            "class_id": class_id,
        })

        bbox = shape_bbox(shape)  # [xmin, ymin, xmax, ymax]
        xmin, ymin, xmax, ymax = bbox
        bbox_rows.append({
            "feature_id": idx,
            "class_name": class_name,
            "class_id": class_id,
            "geom_type": geom_type,
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
            "width": xmax - xmin,
            "height": ymax - ymin,
            "centroid_x": (xmin + xmax) / 2.0,
            "centroid_y": (ymin + ymax) / 2.0,
        })

        features.append({
            "type": "Feature",
            "geometry": geo,
            "properties": props,
        })

    geojson = {
        "type": "FeatureCollection",
        "name": prefix,
        "features": features,
        "properties": {
            "source_shapefile": str(shp_path),
            "class_name": class_name,
            "class_id": class_id,
        },
    }

    geojson_path = out_dir / f"{prefix}.geojson"
    csv_path = out_dir / f"{prefix}_bboxes.csv"

    with geojson_path.open("w", encoding="utf-8") as f:
        json.dump(geojson, f, ensure_ascii=False, indent=2)

    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(bbox_rows[0].keys()) if bbox_rows else [])
        if bbox_rows:
            writer.writeheader()
            writer.writerows(bbox_rows)

    summary = {
        "source_shapefile": str(shp_path),
        "output_dir": str(out_dir),
        "feature_count": len(features),
        "geometry_types": geom_types,
        "geojson_path": str(geojson_path),
        "csv_path": str(csv_path),
        "bbox_example": bbox_rows[0] if bbox_rows else {},
    }
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Export ramp shapefile polygons to GeoJSON and bbox CSV.")
    parser.add_argument("--shp", type=Path, default=DEFAULT_SHP, help="Path to the .shp file")
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR, help="Directory to write exports")
    parser.add_argument("--prefix", default="sidewalk_ramps_2010", help="Output filename prefix")
    parser.add_argument("--class-name", default="ramp", help="Class name to embed in exports")
    parser.add_argument("--class-id", type=int, default=2, help="YOLO class id to embed in exports")
    args = parser.parse_args()

    if not args.shp.exists():
        raise SystemExit(f"Shapefile not found: {args.shp}")

    summary = export_shapefile(args.shp, args.out_dir, args.prefix, args.class_name, args.class_id)

    print("Export complete")
    print(f"  Source: {summary['source_shapefile']}")
    print(f"  Features: {summary['feature_count']}")
    print(f"  Geometry types: {summary['geometry_types']}")
    print(f"  GeoJSON: {summary['geojson_path']}")
    print(f"  CSV: {summary['csv_path']}")
    if summary["bbox_example"]:
        print("  First bbox row:", summary["bbox_example"])
    print("\nNext step: overlay the GeoJSON on matching imagery, then convert polygons to YOLO labels if you have aligned raster images.")


if __name__ == "__main__":
    main()

