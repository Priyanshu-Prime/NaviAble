import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from config import ROBOFLOW_API_KEY

from roboflow import Roboflow

if not ROBOFLOW_API_KEY:
    print("Error: ROBOFLOW_API_KEY not set. Add it to your .env file.")
    sys.exit(1)

rf = Roboflow(api_key=ROBOFLOW_API_KEY)
project = rf.workspace("peggy-cikj6").project("stair-and-ramp-qukcn")

available_versions = [v.version for v in project.versions()]
print(f"Found available versions on Roboflow: {available_versions}")

latest_version = available_versions[-1]
print(f"Downloading Version {latest_version}...")

dataset = project.version(latest_version).download("yolov8")

print(f"\nSuccess! Your new dataset is located at: {dataset.location}")
print(f"Your data.yaml file is at: {dataset.location}/data.yaml")
