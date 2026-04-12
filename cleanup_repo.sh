#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

APPLY=false

usage() {
  cat <<'EOF'
Usage: ./cleanup_repo.sh [--apply]

Default mode is dry-run: it shows the files/directories that would be
removed from Git tracking, but does not modify the index.

Use --apply to actually run git rm --cached on generated artifacts,
virtualenvs, datasets, and training outputs.
EOF
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if [[ "${1:-}" == "--apply" ]]; then
  APPLY=true
elif [[ -n "${1:-}" ]]; then
  echo "Unknown argument: $1"
  usage
  exit 1
fi

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  echo "Error: run this script from inside a Git repository."
  exit 1
fi

DIRS=(
  ".venv"
  "dataset"
  "NaviAble_Dataset"
  "labels_out"
  "stair-and-ramp-2"
  "Ramps_v2"
  "ramp_exports"
  "NaviAble_RoBERTa_Checkpoints"
  "NaviAble_RoBERTa_Final"
  "runs"
  "models"
  "NaviAble_Week5"
)

FILES=(
  "*.pt"
  "*.bin"
  "*.safetensors"
  "*.log"
  "nohup.out"
  "accessibility_reviews.csv"
  "production_roberta_dataset.csv"
  "production_roberta_balanced.csv"
  "targeted_accessibility_reviews.csv"
  "gold_standard_labels_groq.csv"
  "new_mined_data.csv"
  "NaviAble_Final_Training_Data.csv"
  "merge_data.csv"
)

remove_pathspecs=()
for d in "${DIRS[@]}"; do
  remove_pathspecs+=("$d")
done
for f in "${FILES[@]}"; do
  remove_pathspecs+=("$f")
done

echo "Repo cleanup helper"
echo "Root: $ROOT_DIR"
echo "Mode: $([[ "$APPLY" == true ]] && echo apply || echo dry-run)"
echo

echo "Paths to untrack:"
for p in "${remove_pathspecs[@]}"; do
  echo "  - $p"
done

echo
if [[ "$APPLY" != true ]]; then
  echo "Dry-run only. Re-run with --apply to untrack these paths from Git."
  exit 0
fi

echo "Untracking generated artifacts..."
git rm -r --cached --ignore-unmatch -- "${remove_pathspecs[@]}"

echo
echo "Done. Current git status:"
git status --short

