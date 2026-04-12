"""Evaluation helper: run validation and save summary CSV.

Usage:
  python utils/eval.py --weights runs/exp/weights/best.pt --data /path/to/data.yaml --out results.csv
"""
import argparse
import csv
from ultralytics import YOLO


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--weights", required=True)
    parser.add_argument("--data", required=True)
    parser.add_argument("--out", default="eval_report.csv")
    args = parser.parse_args()

    model = YOLO(args.weights)
    print("Running validation...")
    res = model.val(data=args.data)
    # res.boxes and res.metrics differ by ultralytics version; print summary
    summary = []
    if hasattr(res, 'metrics'):
        m = res.metrics
        summary.append(("mAP50", m.get('map50', '')))
        summary.append(("mAP50-95", m.get('map', '')))
        summary.append(("precision", m.get('precision', '')))
        summary.append(("recall", m.get('recall', '')))
    else:
        # fallback to printing object
        summary.append(("result", str(res)))

    with open(args.out, 'w', newline='') as fh:
        writer = csv.writer(fh)
        writer.writerow(['metric','value'])
        for k,v in summary:
            writer.writerow([k,v])

    print(f"Wrote evaluation summary to {args.out}")


if __name__ == '__main__':
    main()

