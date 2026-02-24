import xml.etree.ElementTree as ET
import os

def convert_to_yolo(size, box):
    """Converts pixel coordinates to normalized YOLO format."""
    dw = 1. / size[0]
    dh = 1. / size[1]
    # x_center, y_center, width, height (all normalized 0-1)
    x = (box[0] + box[1]) / 2.0
    y = (box[2] + box[3]) / 2.0
    w = box[1] - box[0]
    h = box[3] - box[2]
    return (x * dw, y * dh, w * dw, h * dh)

# The exact labels found in your wm_annotations.xml
classes = ["step", "stair", "ramp", "grab_bar"]

def convert_xml_to_txt(xml_file, output_dir):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    tree = ET.parse(xml_file)
    root = tree.getroot()
    count = 0

    # Iterate through each image in the XML
    for img in root.findall('image'):
        # images/000143519.jpg -> 000143519.txt
        raw_name = img.get('name')
        file_name = os.path.basename(raw_name).rsplit('.', 1)[0] + ".txt"
        
        width = int(img.get('width'))
        height = int(img.get('height'))

        lines = []
        for box in img.findall('box'):
            label = box.get('label')
            if label not in classes:
                continue
            
            class_id = classes.index(label)
            
            # Using the exact attributes from your file: xtl, xbr, ytl, ybr
            coords = (
                float(box.get('xtl')), 
                float(box.get('xbr')), 
                float(box.get('ytl')), 
                float(box.get('ybr'))
            )
            
            yolo_coords = convert_to_yolo((width, height), coords)
            lines.append(f"{class_id} {' '.join([f'{c:.6f}' for c in yolo_coords])}")

        # Only create a file if it has annotations
        if lines:
            output_path = os.path.join(output_dir, file_name)
            with open(output_path, 'w') as f:
                f.write('\n'.join(lines))
            count += 1

    print(f"Done! Created {count} annotation files in '{output_dir}'.")

if __name__ == "__main__":
    # Using raw string (r'') for Windows path safety
    xml_input_path = r'dataset\wm_annotations.xml'
    output_folder = 'labels_out'
    
    if os.path.exists(xml_input_path):
        convert_xml_to_txt(xml_input_path, output_folder)
    else:
        print(f"Error: Could not find '{xml_input_path}'. Check your folder names.")