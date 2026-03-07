from ultralytics import YOLO

# Windows requires this block to handle multi-threading properly
if __name__ == '__main__':
    # 1. Initialize the YOLOv11 Nano architecture
    model = YOLO("yolo11n.pt") 

    # 2. Define the path to your dataset
    dataset_yaml = "C:/Users/priya.ASUS-LAPTOP/Music/NaviAble_Project/stair-and-ramp-2/data.yaml"

    # 3. Execute training
    print("Starting Week 5 Comparative Training...")
    results = model.train(
        data=dataset_yaml, 
        epochs=25,          
        imgsz=640,          
        device="cuda",      
        project="NaviAble_Week5",
        name="YOLOv11_Roboflow_Dataset",
        batch=8,
        workers=2
    )

    print("Training Complete! Check the 'NaviAble_Week5' folder for your graphs.")