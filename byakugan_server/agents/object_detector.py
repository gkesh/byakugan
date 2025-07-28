from ultralytics import YOLO

import numpy as np
import cv2

class ObjectDetector:
    def __init__(self, weights):
        
        self.model = YOLO('yolov8m-world.pt')
        self.weights = weights
    
    def detect_objects(self, frame):
        """
        Detect objects in frame and return results with weighted importance scores
        """
        results = self.model(frame, conf=0.3, verbose=False)
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                for box in boxes:
                    # Get class name
                    class_id = int(box.cls[0])
                    class_name = self.model.names[class_id]
                    confidence = float(box.conf[0])
                    
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    # Calculate relative position and size
                    frame_height, frame_width = frame.shape[:2]
                    center_x = (x1 + x2) / 2 / frame_width
                    center_y = (y1 + y2) / 2 / frame_height
                    width = (x2 - x1) / frame_width
                    height = (y2 - y1) / frame_height
                    
                    # Get importance weight
                    importance = self.weights.get(class_name, self.weights['default']) # type: ignore
                    
                    detection = {
                        'class': class_name,
                        'confidence': confidence,
                        'bbox': [x1, y1, x2, y2],
                        'center': [center_x, center_y],
                        'size': [width, height],
                        'importance': importance,
                        'position_desc': self._get_position_description(center_x, center_y)
                    }
                    detections.append(detection)
        
        return sorted(detections, key=lambda x: x['importance'], reverse=True)
    
    def _get_position_description(self, x, y):
        horizontal = "center"
        if x < 0.33:
            horizontal = "right"
        elif x > 0.67:
            horizontal = "left"
        
        vertical = "middle"
        if y < 0.33:
            vertical = "top"
        elif y > 0.67:
            vertical = "bottom"
        
        return f"{vertical}-{horizontal}"
