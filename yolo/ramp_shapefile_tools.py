"""Tools for the ramp shapefile.

This script can:
  1) render a quick overlay/preview PNG of the ramp features, and
  2) export point/bbox labels in YOLO format for a georeferenced raster tile.

The `Sidewalk_Ramps_2010` layer in this repo contains point features, so the
YOLO export treats each point as a small box centered on the projected point.
For real training, use it only when you have matching imagery and known raster
bounds.
"""
from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any, Iterable, List, Sequence, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import shapefile  # type: ignore


DEFAULT_SHP = Path(
    "/Users/vedantsunillande/spot-repo/NaviAble/NaviAble/Ramps_v2/Sidewalk_Ramps_2010/Sidewalk_Ramps_2010.shp"
)
DEFAULT_OUT_DIR = Path(
    "/Users/vedantsunillande/spot-repo/NaviAble/NaviAble/ramp_exports"
)


def _shape_points(shape: Any) -> List[Tuple[float, float]]:
    return [(float(x), float(y)) for x, y in getattr(shape, "points", [])]


def _shape_bbox(shape: Any) -> Tuple[float, float, float, float]:
    bbox = getattr(shape, "bbox", None)
    if bbox and len(bbox) == 4:
        return float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
    pts = _shape_points(shape)
    if not pts:
        return 0.0, 0.0, 0.0, 0.0
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def _read_shapes(shp_path: Path) -> List[Any]:
    reader = shapefile.Reader(str(shp_path))
    return list(reader.shapes())


def _collect_xy(shapes: Iterable[Any]) -> Tuple[List[float], List[float]]:
    xs: List[float] = []
    ys: List[float] = []
    for shape in shapes:
        pts = _shape_points(shape)
        if pts:
            for x, y in pts:
                xs.append(x)
                ys.append(y)
        else:
            xmin, ymin, xmax, ymax = _shape_bbox(shape)
            xs.extend([xmin, xmax])
            ys.extend([ymin, ymax])
    return xs, ys


def render_overlay(shp_path: Path, out_png: Path, title: str | None = None) -> dict:
    shapes = _read_shapes(shp_path)
    xs, ys = _collect_xy(shapes)

    if not xs or not ys:
        raise RuntimeError(f"No coordinate data found in {shp_path}")

    out_png.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(10, 10), dpi=160)

    point_xs: List[float] = []
    point_ys: List[float] = []
    for shape in shapes:
        pts = _shape_points(shape)
        if len(pts) == 1:
            x, y = pts[0]
            point_xs.append(x)
            point_ys.append(y)
        elif len(pts) > 1:
            px = [p[0] for p in pts]
            py = [p[1] for p in pts]
            ax.plot(px, py, color="#e74c3c", linewidth=0.3, alpha=0.2)
        else:
            xmin, ymin, xmax, ymax = _shape_bbox(shape)
            point_xs.append((xmin + xmax) / 2.0)
            point_ys.append((ymin + ymax) / 2.0)

    if point_xs:
        ax.scatter(point_xs, point_ys, s=2, c="#e74c3c", alpha=0.35)

    ax.set_aspect("equal", adjustable="box")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.set_title(title or shp_path.stem)
    ax.grid(True, linewidth=0.3, alpha=0.25)
    fig.tight_layout()
    fig.savefig(out_png)
    plt.close(fig)

    return {"feature_count": len(shapes), "output_png": str(out_png)}


def _map_to_pixel(x: float, y: float, bounds: Sequence[float], image_width: int, image_height: int) -> Tuple[float, float]:
    xmin, ymin, xmax, ymax = bounds
    px = (x - xmin) / (xmax - xmin) * image_width if xmax != xmin else image_width / 2.0
    py = (ymax - y) / (ymax - ymin) * image_height if ymax != ymin else image_height / 2.0
    return px, py


def export_yolo_labels(
    shp_path: Path,
    out_dir: Path,
    image_name: str,
    image_width: int,
    image_height: int,
    bounds: Sequence[float] | None,
    class_id: int,
    box_px: int,
) -> dict:
    reader = shapefile.Reader(str(shp_path))
    shapes = list(reader.shapes())
    out_dir.mkdir(parents=True, exist_ok=True)

    if bounds is None:
        bounds = _shape_bbox(shapes[0]) if shapes else (0.0, 0.0, 0.0, 0.0)
        for shape in shapes[1:]:
            xmin, ymin, xmax, ymax = _shape_bbox(shape)
            bxmin, bymin, bxmax, bymax = bounds
            bounds = (min(bxmin, xmin), min(bymin, ymin), max(bxmax, xmax), max(bymax, ymax))

    label_path = out_dir / f"{Path(image_name).stem}.txt"
    half_w = max(1, box_px) / 2.0
    half_h = max(1, box_px) / 2.0

    lines: List[str] = []
    for shape in shapes:
        pts = _shape_points(shape)
        if pts:
            x, y = pts[0]
        else:
            xmin, ymin, xmax, ymax = _shape_bbox(shape)
            x = (xmin + xmax) / 2.0
            y = (ymin + ymax) / 2.0

        px, py = _map_to_pixel(x, y, bounds, image_width, image_height)
        x1 = max(0.0, px - half_w)
        y1 = max(0.0, py - half_h)
        x2 = min(float(image_width), px + half_w)
        y2 = min(float(image_height), py + half_h)
        bw = max(1.0, x2 - x1)
        bh = max(1.0, y2 - y1)
        xc = x1 + bw / 2.0
        yc = y1 + bh / 2.0
        lines.append(
            f"{class_id} {xc / image_width:.6f} {yc / image_height:.6f} {bw / image_width:.6f} {bh / image_height:.6f}"
        )

    label_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
    return {
        "feature_count": len(shapes),
        "output_label": str(label_path),
        "bounds_used": tuple(bounds),
        "image_width": image_width,
        "image_height": image_height,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ramp shapefile utilities")
    parser.add_argument("--shp", type=Path, default=DEFAULT_SHP)
    parser.add_argument("--mode", choices=["overlay", "labels"], required=True)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--out", type=Path, help="Output PNG path for overlay mode")
    parser.add_argument("--image-name", default="ramp_tile")
    parser.add_argument("--image-width", type=int, default=1024)
    parser.add_argument("--image-height", type=int, default=1024)
    parser.add_argument("--bounds", nargs=4, type=float, metavar=("XMIN", "YMIN", "XMAX", "YMAX"))
    parser.add_argument("--class-id", type=int, default=2)
    parser.add_argument("--box-px", type=int, default=12)
    parser.add_argument("--title", default=None)
    args = parser.parse_args()

    if not args.shp.exists():
        raise SystemExit(f"Shapefile not found: {args.shp}")

    if args.mode == "overlay":
        out_png = args.out or (args.out_dir / f"{args.shp.stem}_overlay.png")
        summary = render_overlay(args.shp, out_png, title=args.title)
        print(f"Overlay written to {summary['output_png']} ({summary['feature_count']} features)")
    else:
        summary = export_yolo_labels(
            args.shp,
            args.out_dir,
            args.image_name,
            args.image_width,
            args.image_height,
            args.bounds,
            args.class_id,
            args.box_px,
        )
        print(f"YOLO labels written to {summary['output_label']} ({summary['feature_count']} features)")
        print(f"Bounds used: {summary['bounds_used']}")


if __name__ == "__main__":
    main()

