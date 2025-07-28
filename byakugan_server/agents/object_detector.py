from ultralytics import YOLO

import numpy as np
import cv2

class ObjectDetector:
    def __init__(self, weights):
        
        self.model = YOLO('yolov8m-world.pt')
        self.weights = weights
    
    def detect_objects(self, frame):
        """Detect objects in frame and return results with importance scores"""
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
        """Convert normalized coordinates to position description"""
        horizontal = "center"
        if x < 0.33:
            horizontal = "left"
        elif x > 0.67:
            horizontal = "right"
        
        vertical = "middle"
        if y < 0.33:
            vertical = "top"
        elif y > 0.67:
            vertical = "bottom"
        
        return f"{vertical}-{horizontal}"


class AdvancedObjectDetector:
    """
    Advanced models include additional information from the frame such as 
    trajectory and potential velocity, but this requires longer computation per frame requiring longer latency.
    
    The model is created to test the upper limits of frame analysis and its impact on the 
    """
    def __init__(self, weights):
        self.model = YOLO('yolov8m-world.pt')
        self.weights = weights
        self.kalman_filters = {}
        self.frame_count = 0
        
    def _create_kalman(self):
        """Create a new Kalman filter for trajectory prediction"""
        kf = cv2.KalmanFilter(4, 2)
        kf.transitionMatrix = np.array([[1,0,1,0],[0,1,0,1],[0,0,1,0],[0,0,0,1]], np.float32)
        kf.measurementMatrix = np.array([[1,0,0,0],[0,1,0,0]], np.float32)
        kf.processNoiseCov = np.eye(4, dtype=np.float32) * 1e-2
        kf.measurementNoiseCov = np.eye(2, dtype=np.float32) * 1e-1
        kf.errorCovPost = np.eye(4, dtype=np.float32)
        return kf
    
    def _calculate_trajectory_risk(self, vx, vy, center_x, center_y, width, height):
        """Calculate trajectory-based risk score"""
        # Speed magnitude
        speed = np.sqrt(vx**2 + vy**2)
        
        # Direction towards camera (negative vy in normalized coords)
        approaching_factor = max(0, -vy * 5)  # Weight objects moving towards camera
        
        # Lateral movement risk (crossing path)
        lateral_risk = abs(vx) * 3
        
        # Central position risk (objects in center are more critical)
        # Consider BOTH horizontal and vertical center positions
        center_x_risk = 1 - (2 * abs(center_x - 0.5))  # Higher for horizontal center
        center_y_risk = 1 - (2 * abs(center_y - 0.5))  # Higher for vertical center
        
        # Combined 2D center risk - objects in true center get highest risk
        center_risk = (center_x_risk + center_y_risk) / 2
        
        # Vertical position modifier - objects in lower half are more critical for ground-based navigation
        vertical_position_factor = 1.0
        if center_y > 0.5:  # Lower half of frame
            vertical_position_factor = 1.2
        elif center_y < 0.3:  # Upper part of frame (sky/background)
            vertical_position_factor = 0.8
        
        # Size factor (larger objects are more critical)
        size_factor = min(width * height * 10, 2.0)
        
        # Combine factors
        trajectory_risk = (speed * 2 + approaching_factor + lateral_risk + center_risk * vertical_position_factor) * size_factor
        
        return min(trajectory_risk, 5.0)  # Cap at 5.0
    
    def _get_movement_description(self, vx, vy):
        """Convert velocity to movement description"""
        speed = np.sqrt(vx**2 + vy**2)
        
        if speed < 0.001:
            return "stationary"
        
        # Determine primary direction
        if abs(vx) > abs(vy):
            horizontal = "moving right" if vx > 0 else "moving left"
            if abs(vy) > 0.0005:
                vertical = " and forward" if vy < 0 else " and backward"
                return horizontal + vertical
            return horizontal
        else:
            vertical = "approaching" if vy < 0 else "moving away"
            if abs(vx) > 0.0005:
                horizontal = " from right" if vx > 0 else " from left"
                return vertical + horizontal
            return vertical

    def detect_objects(self, frame):
        """Detect objects in frame and return results with importance scores and trajectory"""
        self.frame_count += 1
        
        # Run detection with tracking
        results = self.model.track(
            frame,
            conf=0.3,
            persist=True,
            verbose=False
        )
        
        detections = []
        
        for result in results:
            boxes = result.boxes
            if boxes is not None:
                # Get tracking IDs if available
                ids = boxes.id if boxes.id is not None else [0] * len(boxes.cls)
                
                for box, track_id in zip(boxes, ids): # type: ignore
                    # Get class info
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
                    
                    # Kalman filter for trajectory prediction
                    cx_pixel = (x1 + x2) / 2
                    cy_pixel = (y1 + y2) / 2
                    
                    track_id = int(track_id) if track_id is not None else 0
                    
                    if track_id not in self.kalman_filters:
                        kf = self._create_kalman()
                        kf.statePost = np.array([[cx_pixel], [cy_pixel], [0], [0]], np.float32)
                        self.kalman_filters[track_id] = kf
                        vx, vy = 0, 0  # No velocity for first detection
                        px, py = cx_pixel, cy_pixel
                    else:
                        kf = self.kalman_filters[track_id]
                        px, py, vx, vy = kf.predict().flatten()
                        kf.correct(np.array([[cx_pixel], [cy_pixel]], np.float32))
                        
                        # Convert velocity to normalized coordinates
                        vx = vx / frame_width
                        vy = vy / frame_height
                    
                    # Get base importance weight
                    base_importance = self.weights.get(class_name, self.weights['default'])
                    
                    # Calculate trajectory risk
                    trajectory_risk = self._calculate_trajectory_risk(vx, vy, center_x, center_y, width, height)
                    
                    # Combine base importance with trajectory risk
                    total_importance = base_importance + trajectory_risk
                    
                    detection = {
                        'class': class_name,
                        'confidence': confidence,
                        'bbox': [x1, y1, x2, y2],
                        'center': [center_x, center_y],
                        'size': [width, height],
                        'importance': total_importance,
                        'base_importance': base_importance,
                        'trajectory_risk': trajectory_risk,
                        'velocity': [vx, vy],
                        'predicted_pos': [px / frame_width, py / frame_height],
                        'movement_desc': self._get_movement_description(vx, vy),
                        'position_desc': self._get_position_description(center_x, center_y),
                        'track_id': track_id
                    }
                    detections.append(detection)
        
        return sorted(detections, key=lambda x: x['importance'], reverse=True)
    
    def _get_position_description(self, x, y):
        """Convert normalized coordinates to position description"""
        horizontal = "center"
        if x < 0.33:
            horizontal = "left"
        elif x > 0.67:
            horizontal = "right"
        
        vertical = "middle" 
        if y < 0.33:
            vertical = "top"
        elif y > 0.67:
            vertical = "bottom"
            
        return f"{vertical}-{horizontal}"
