"""Hybrid YOLO + CLIP accessibility detector.

Workflow:
1. Use YOLO to propose candidate regions.
2. Use CLIP text-image similarity to classify each crop as one of:
   - ramp
   - stair
   - step
   - guard rail
   - negative
3. Draw the result on the image and optionally save JSON predictions.

This is intentionally lightweight and works with the repo's macOS MPS setup.
It uses `transformers` CLIP components so you do not need the separate `clip`
package installed.
"""
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple

import cv2
import numpy as np
import torch
from PIL import Image
from ultralytics import YOLO
from transformers import CLIPModel, CLIPProcessor


GUARD_RAIL_LABEL = "guard rail"

ACCESSIBILITY_PROMPTS: Dict[str, List[str]] = {
    "ramp": [
        "a wheelchair ramp",
        "a sloped accessibility ramp",
        "a ramp for disabled access",
        "an outdoor wheelchair ramp",
    ],
    "stair": [
        "a staircase",
        "a staircase with multiple steps",
        "stairs in a building",
        "an indoor staircase",
    ],
    "step": [
        "a single step",
        "a small stair step",
        "one step in a walkway",
        "a curb step",
    ],
    GUARD_RAIL_LABEL: [
        "a guard rail",
        "a handrail beside stairs",
        "a metal handrail",
        "a safety rail next to steps",
    ],
    "negative": [
        "flat ground",
        "no accessibility structure",
        "an empty sidewalk",
        "plain pavement",
    ],
}
CLASS_ORDER = ["ramp", "stair", "step", GUARD_RAIL_LABEL, "negative"]
CLASS_COLORS = {
    "ramp": (0, 180, 0),
    "stair": (0, 165, 255),
    "step": (255, 165, 0),
    GUARD_RAIL_LABEL: (255, 0, 255),
    "negative": (128, 128, 128),
}


@dataclass
class Prediction:
    bbox: Tuple[int, int, int, int]
    yolo_conf: float
    clip_conf: float
    fused_conf: float
    label: str


def resolve_device(preferred: str | None = None) -> str:
    if preferred:
        return preferred
    if torch.backends.mps.is_available():
        return "mps"
    if torch.cuda.is_available():
        return "cuda"
    return "cpu"


def load_clip(model_name: str, device: str) -> Tuple[CLIPModel, CLIPProcessor]:
    processor = CLIPProcessor.from_pretrained(model_name)
    model = CLIPModel.from_pretrained(model_name)
    model.to(device)
    model.eval()
    return model, processor


def load_images(source: Path) -> List[Path]:
    if not source.exists():
        raise FileNotFoundError(
            f"Source path does not exist: {source}. Replace the placeholder path with a real image file or directory."
        )
    if source.is_dir():
        exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}
        return sorted([p for p in source.iterdir() if p.suffix.lower() in exts])
    if source.is_file():
        return [source]
    raise FileNotFoundError(
        f"Unsupported source path: {source}. Provide a real image file or a directory of images."
    )


def crop_box(frame: np.ndarray, box: Sequence[float]) -> np.ndarray | None:
    x1, y1, x2, y2 = [int(round(v)) for v in box]
    h, w = frame.shape[:2]
    x1 = max(0, min(x1, w - 1))
    y1 = max(0, min(y1, h - 1))
    x2 = max(0, min(x2, w))
    y2 = max(0, min(y2, h))
    if x2 <= x1 or y2 <= y1:
        return None
    crop = frame[y1:y2, x1:x2]
    return crop if crop.size else None


def build_text_inventory() -> Tuple[List[str], Dict[str, slice]]:
    prompts: List[str] = []
    class_slices: Dict[str, slice] = {}
    start = 0
    for cls in CLASS_ORDER:
        cls_prompts = ACCESSIBILITY_PROMPTS[cls]
        prompts.extend(cls_prompts)
        class_slices[cls] = slice(start, start + len(cls_prompts))
        start += len(cls_prompts)
    return prompts, class_slices


def classify_crops(
    crop_images: List[Image.Image],
    clip_model: CLIPModel,
    clip_processor: CLIPProcessor,
    device: str,
) -> List[Tuple[str, float]]:
    if not crop_images:
        return []

    text_prompts, class_slices = build_text_inventory()
    inputs = clip_processor(text=text_prompts, images=crop_images, return_tensors="pt", padding=True)
    inputs = {k: v.to(device) for k, v in inputs.items()}

    with torch.no_grad():
        outputs = clip_model(**inputs)
        logits = outputs.logits_per_image
        probs = logits.softmax(dim=-1)

    results: List[Tuple[str, float]] = []
    for i in range(probs.shape[0]):
        class_scores: Dict[str, float] = {}
        for cls in CLASS_ORDER:
            idx = class_slices[cls]
            class_scores[cls] = float(probs[i, idx].mean().item())

        positive_scores = {k: v for k, v in class_scores.items() if k != "negative"}
        best_positive = max(positive_scores, key=positive_scores.get)
        best_positive_score = positive_scores[best_positive]
        negative_score = class_scores["negative"]

        if negative_score >= best_positive_score or best_positive_score < 0.15:
            results.append(("negative", negative_score))
        else:
            results.append((best_positive, best_positive_score))

    return results


def fuse_scores(yolo_conf: float, clip_conf: float, alpha: float = 0.35) -> float:
    return float(alpha * yolo_conf + (1.0 - alpha) * clip_conf)


def annotate(frame: np.ndarray, prediction: Prediction) -> None:
    x1, y1, x2, y2 = prediction.bbox
    color = CLASS_COLORS.get(prediction.label, (0, 255, 0))
    label = f"{prediction.label} | y:{prediction.yolo_conf:.2f} c:{prediction.clip_conf:.2f} f:{prediction.fused_conf:.2f}"
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    y_text = max(20, y1 - 8)
    cv2.putText(frame, label, (x1, y_text), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2, cv2.LINE_AA)


def predict_image(
    image_path: Path,
    yolo_model: YOLO,
    clip_model: CLIPModel,
    clip_processor: CLIPProcessor,
    device: str,
    imgsz: int,
    conf: float,
    max_det: int,
    fallback_full_image: bool,
) -> Tuple[np.ndarray, List[Prediction]]:
    frame = cv2.imread(str(image_path))
    if frame is None:
        raise RuntimeError(f"Could not read image: {image_path}")

    results = yolo_model.predict(source=frame, imgsz=imgsz, conf=conf, verbose=False, device=device)[0]
    boxes = results.boxes

    candidate_boxes: List[Tuple[Sequence[float], float]] = []
    if boxes is not None and len(boxes) > 0:
        order = np.argsort(-boxes.conf.cpu().numpy())[:max_det]
        for idx in order:
            candidate_boxes.append((boxes.xyxy[idx].cpu().numpy().tolist(), float(boxes.conf[idx].item())))
    elif fallback_full_image:
        h, w = frame.shape[:2]
        candidate_boxes.append(([0, 0, w, h], conf))

    crops: List[Image.Image] = []
    kept_boxes: List[Tuple[Sequence[float], float]] = []
    for box, yolo_conf in candidate_boxes:
        crop = crop_box(frame, box)
        if crop is None:
            continue
        rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        crops.append(Image.fromarray(rgb))
        kept_boxes.append((box, yolo_conf))

    clip_results = classify_crops(crops, clip_model, clip_processor, device)
    predictions: List[Prediction] = []

    for (box, yolo_conf), (label, clip_conf) in zip(kept_boxes, clip_results):
        fused = fuse_scores(yolo_conf, clip_conf)
        x1, y1, x2, y2 = [int(round(v)) for v in box]
        predictions.append(
            Prediction(
                bbox=(x1, y1, x2, y2),
                yolo_conf=yolo_conf,
                clip_conf=clip_conf,
                fused_conf=fused,
                label=label,
            )
        )

    for pred in predictions:
        annotate(frame, pred)

    return frame, predictions


def main() -> None:
    parser = argparse.ArgumentParser(description="Hybrid YOLO + CLIP accessibility detector")
    parser.add_argument("--source", required=True, type=Path, help="Image file or directory")
    parser.add_argument("--weights", default="yolo11n.pt", help="YOLO weights path")
    parser.add_argument("--clip-model", default="openai/clip-vit-base-patch32", help="CLIP model id")
    parser.add_argument("--device", default=None, help="mps, cuda, or cpu")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--conf", type=float, default=0.25)
    parser.add_argument("--max-det", type=int, default=10)
    parser.add_argument("--fallback-full-image", action="store_true", help="Classify the whole image if YOLO finds nothing")
    parser.add_argument("--output-dir", type=Path, default=Path("runs/hybrid_accessibility"))
    parser.add_argument("--save-json", action="store_true", help="Write per-image JSON predictions")
    parser.add_argument("--show", action="store_true", help="Display a window with the annotated result")
    args = parser.parse_args()

    device = resolve_device(args.device)
    yolo_model = YOLO(args.weights)
    clip_model, clip_processor = load_clip(args.clip_model, device)

    images = load_images(args.source)
    if args.source.is_dir() and not images:
        raise SystemExit(
            f"No supported image files found in directory: {args.source}. "
            "Use a folder containing .jpg/.jpeg/.png/.bmp/.webp/.tif/.tiff files."
        )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    summaries: List[dict] = []

    for image_path in images:
        annotated, predictions = predict_image(
            image_path=image_path,
            yolo_model=yolo_model,
            clip_model=clip_model,
            clip_processor=clip_processor,
            device=device,
            imgsz=args.imgsz,
            conf=args.conf,
            max_det=args.max_det,
            fallback_full_image=args.fallback_full_image,
        )

        out_image = args.output_dir / image_path.name
        cv2.imwrite(str(out_image), annotated)

        summary = {
            "image": str(image_path),
            "output_image": str(out_image),
            "predictions": [
                {
                    "bbox": list(pred.bbox),
                    "label": pred.label,
                    "yolo_conf": round(pred.yolo_conf, 4),
                    "clip_conf": round(pred.clip_conf, 4),
                    "fused_conf": round(pred.fused_conf, 4),
                }
                for pred in predictions
            ],
        }
        summaries.append(summary)

        if args.save_json:
            json_path = args.output_dir / f"{image_path.stem}.json"
            json_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")

        print(f"{image_path.name}: {len(predictions)} proposals -> {out_image}")
        for pred in predictions[:5]:
            print(
                f"  - {pred.label:11s} yolo={pred.yolo_conf:.2f} clip={pred.clip_conf:.2f} fused={pred.fused_conf:.2f} bbox={pred.bbox}"
            )

        if args.show:
            cv2.imshow("Hybrid Accessibility Detector", annotated)
            cv2.waitKey(0)
            cv2.destroyAllWindows()

    if args.save_json and len(images) > 1:
        (args.output_dir / "summary.json").write_text(json.dumps(summaries, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()

