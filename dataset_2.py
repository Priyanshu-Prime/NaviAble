# Install required libraries if you haven't already
# pip install roboflow ultralytics

from roboflow import Roboflow

# 1. Authenticate with your Roboflow API Key
rf = Roboflow(api_key="yxXZ8uXnJ58aKW3xIW0z")

project = rf.workspace("peggy-cikj6").project("stair-and-ramp-qukcn")

# 3. Automatically find the active versions
available_versions = [v.version for v in project.versions()]
print(f"Found available versions on Roboflow: {available_versions}")

# Grab the latest version dynamically (the last one in the list)
latest_version = available_versions[-1]
print(f"Downloading Version {latest_version}...")

# 4. Download the dataset in YOLO format
dataset = project.version(latest_version).download("yolov8")

print(f"\nSuccess! Your new dataset is located at: {dataset.location}")
print(f"Your data.yaml file is at: {dataset.location}/data.yaml")