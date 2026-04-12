"""Compute YOLO anchors via k-means on dataset labels.

Usage:
  python compute_anchors.py --data /path/to/data.yaml --k 9 --out anchors.txt

This script loads label files in the dataset labels directory (labels/*.txt or labels/train/*.txt)
and runs k-means on box widths/heights (normalized). It writes anchors as 'w,h' pairs.
"""
import argparse
import glob
import os
import numpy as np


def load_boxes(labels_paths):
    boxes = []
    for p in labels_paths:
        for f in glob.glob(os.path.join(p, "*.txt")):
            with open(f) as fh:
                for line in fh:
                    parts = line.strip().split()
                    if len(parts) < 5:
                        continue
                    # yolo format: class x_center y_center width height (normalized)
                    w = float(parts[3])
                    h = float(parts[4])
                    boxes.append([w, h])
    return np.array(boxes)


def kmeans(boxes, k, max_iter=1000):
    # initialize centroids randomly
    idx = np.random.choice(len(boxes), k, replace=False)
    centroids = boxes[idx]
    for it in range(max_iter):
        dists = np.sqrt(((boxes[:, None, :] - centroids[None, :, :]) ** 2).sum(axis=2))
        labels = dists.argmin(axis=1)
        new_centroids = np.array([boxes[labels == i].mean(axis=0) if np.any(labels == i) else centroids[i] for i in range(k)])
        if np.allclose(new_centroids, centroids):
            break
        centroids = new_centroids
    return centroids


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--labels", nargs="*", default=[], help="paths to labels folders or pattern")
    parser.add_argument("--k", type=int, default=9)
    parser.add_argument("--out", default="anchors.txt")
    args = parser.parse_args()

    # If no labels provided, try common locations
    labels_paths = args.labels or [
        os.path.join(os.path.dirname(__file__), "..", "labels_out"),
        os.path.join(os.path.dirname(__file__), "..", "labels"),
        os.path.join(os.path.dirname(__file__), "..", "NaviAble_Dataset", "train", "labels"),
    ]

    boxes = load_boxes(labels_paths)
    if len(boxes) == 0:
        print("No boxes found in provided label paths:", labels_paths)
        return

    centroids = kmeans(boxes, args.k)
    # sort by width
    centroids = centroids[centroids[:, 0].argsort()]
    lines = [f"{w:.6f},{h:.6f}" for w, h in centroids]
    with open(args.out, "w") as fh:
        fh.write("\n".join(lines))
    print(f"Wrote {len(lines)} anchors to {args.out}")


if __name__ == "__main__":
    main()

