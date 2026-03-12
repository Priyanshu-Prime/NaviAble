import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
PROJECT_ROOT = Path(__file__).resolve().parent
load_dotenv(PROJECT_ROOT / ".env")

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
ROBOFLOW_API_KEY = os.getenv("ROBOFLOW_API_KEY")

# Common paths
DATASET_DIR = PROJECT_ROOT / "dataset"
LABELS_OUT_DIR = PROJECT_ROOT / "labels_out"
NAVIABLE_DATASET_DIR = PROJECT_ROOT / "NaviAble_Dataset"
ROBERTA_CHECKPOINTS_DIR = PROJECT_ROOT / "NaviAble_RoBERTa_Checkpoints"
ROBERTA_FINAL_DIR = PROJECT_ROOT / "NaviAble_RoBERTa_Final"

# YOLO class names
YOLO_CLASSES = ["step", "stair", "ramp", "grab_bar"]
