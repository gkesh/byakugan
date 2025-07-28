import numpy as np

class SceneDescriber:
    def create_scene_description(self, detections):
        """Create a comprehensive scene description from detections"""
        if not detections:
            return "The path ahead appears clear with no significant obstacles detected."
        
        # Categorize detections by importance
        critical_obstacles = [d for d in detections if d['importance'] >= 8]
        moderate_obstacles = [d for d in detections if 5 <= d['importance'] < 8]
        minor_obstacles = [d for d in detections if d['importance'] < 5]
        
        description_parts = []
        
        # Present objects in scence different based on severity, using predefined ruleset
        if critical_obstacles:
            critical_desc = self._describe_obstacles(critical_obstacles, "CRITICAL")
            description_parts.append(critical_desc)
        
        if moderate_obstacles:
            moderate_desc = self._describe_obstacles(moderate_obstacles, "MODERATE")
            description_parts.append(moderate_desc)
        
        if minor_obstacles and len(minor_obstacles) > 0:
            minor_count = len(minor_obstacles)
            description_parts.append(f"Additionally, there are {minor_count} minor items in the scene.")
        
        return " ".join(description_parts)
    
    def _describe_obstacles(self, obstacles, priority_level):
        """Describe a group of obstacles"""
        if not obstacles:
            return ""
        
        descriptions = []
        for obs in obstacles:
            size_desc = "large" if obs['size'][0] * obs['size'][1] > 0.1 else "small"
            desc = f"{size_desc} {obs['class']} in the {obs['position_desc']} area"
            descriptions.append(desc)
        
        priority_text = f"{priority_level} ALERT: " if priority_level == "CRITICAL" else ""
        return f"{priority_text}Detected {', '.join(descriptions)}."


class AdvancedSceneDetector:
    def create_scene_description(self, detections, frame_shape):
        """Create a comprehensive scene description from detections including trajectory info"""
        if not detections:
            return "The path ahead appears clear with no significant obstacles detected."
        
        frame_height, frame_width = frame_shape[:2]
        
        # Categorize detections by total importance (base + trajectory)
        critical_obstacles = [d for d in detections if d['importance'] >= 8]
        moderate_obstacles = [d for d in detections if 5 <= d['importance'] < 8]
        minor_obstacles = [d for d in detections if d['importance'] < 5]
        
        # Separate by movement type
        moving_objects = [d for d in detections if np.sqrt(d['velocity'][0]**2 + d['velocity'][1]**2) > 0.001]
        stationary_objects = [d for d in detections if np.sqrt(d['velocity'][0]**2 + d['velocity'][1]**2) <= 0.001]
        
        # Analyze spatial distribution using frame_shape
        spatial_analysis = self._analyze_spatial_distribution(detections)
        
        # Check for collision trajectories
        collision_warnings = self._check_collision_trajectories(moving_objects)
        
        description_parts = []
        
        # Add collision warnings first if any
        if collision_warnings:
            description_parts.append(collision_warnings)
        
        # Describe critical obstacles first with trajectory info
        if critical_obstacles:
            critical_desc = self._describe_obstacles_with_trajectory(critical_obstacles, "CRITICAL", frame_width, frame_height)
            description_parts.append(critical_desc)
        
        # Describe moderate obstacles
        if moderate_obstacles:
            moderate_desc = self._describe_obstacles_with_trajectory(moderate_obstacles, "MODERATE", frame_width, frame_height)
            description_parts.append(moderate_desc)
        
        # Add spatial distribution info
        if spatial_analysis:
            description_parts.append(spatial_analysis)
        
        # Add movement summary
        if moving_objects:
            movement_summary = self._create_movement_summary(moving_objects, frame_height)
            description_parts.append(movement_summary)
        
        # Briefly mention minor obstacles
        if minor_obstacles and len(minor_obstacles) > 0:
            minor_count = len(minor_obstacles)
            description_parts.append(f"Additionally, there are {minor_count} minor items in the scene.")
        
        return " ".join(description_parts)
    
    def _describe_obstacles_with_trajectory(self, obstacles, priority_level, frame_width, frame_height):
        """Describe obstacles including their trajectory information"""
        if not obstacles:
            return ""
        
        descriptions = []
        for obs in obstacles:
            size_desc = "large" if obs['size'][0] * obs['size'][1] > 0.1 else "small"
            
            # Calculate actual pixel distances for better context
            pixel_width = obs['size'][0] * frame_width
            pixel_height = obs['size'][1] * frame_height
            
            # Add trajectory information with distance context
            trajectory_info = ""
            if obs['trajectory_risk'] > 1.0:
                # Calculate estimated time to reach center (if moving toward it)
                if abs(obs['velocity'][0]) > 0.001 or abs(obs['velocity'][1]) > 0.001:
                    # Distance to both horizontal and vertical center
                    distance_to_center_x = abs(obs['center'][0] - 0.5)
                    distance_to_center_y = abs(obs['center'][1] - 0.5)
                    total_distance_to_center = np.sqrt(distance_to_center_x**2 + distance_to_center_y**2)
                    
                    speed = np.sqrt(obs['velocity'][0]**2 + obs['velocity'][1]**2)
                    if speed > 0.001:
                        frames_to_center = total_distance_to_center / speed
                        if frames_to_center < 30:  # Less than 1 second at 30fps
                            trajectory_info = f" ({obs['movement_desc']}, immediate concern)"
                        else:
                            trajectory_info = f" ({obs['movement_desc']})"
                    else:
                        trajectory_info = f" ({obs['movement_desc']})"
            
            desc = f"{size_desc} {obs['class']} in the {obs['position_desc']} area{trajectory_info}"
            descriptions.append(desc)
        
        priority_text = f"{priority_level} ALERT: " if priority_level == "CRITICAL" else ""
        return f"{priority_text}Detected {', '.join(descriptions)}."
    
    def _create_movement_summary(self, moving_objects, frame_height):
        """Create a summary of object movements using frame dimensions"""
        if not moving_objects:
            return ""
        
        approaching = [obj for obj in moving_objects if obj['velocity'][1] < -0.002]
        crossing = [obj for obj in moving_objects if abs(obj['velocity'][0]) > 0.002]
        
        summary_parts = []
        
        if approaching:
            classes = [obj['class'] for obj in approaching[:3]]  # Limit to first 3
            # Calculate average approach speed in pixels per frame
            avg_speed = np.mean([abs(obj['velocity'][1]) * frame_height for obj in approaching])
            speed_desc = "rapidly" if avg_speed > 5 else "slowly"
            summary_parts.append(f"Movement detected: {', '.join(classes)} approaching {speed_desc}")
        
        if crossing:
            classes = [obj['class'] for obj in crossing[:2]]  # Limit to first 2
            # Determine crossing direction and speed
            left_to_right = sum(1 for obj in crossing if obj['velocity'][0] > 0)
            right_to_left = len(crossing) - left_to_right
            
            direction_desc = ""
            if left_to_right > right_to_left:
                direction_desc = " (left to right)"
            elif right_to_left > left_to_right:
                direction_desc = " (right to left)"
            
            summary_parts.append(f"{', '.join(classes)} crossing path{direction_desc}")
        
        return "Movement analysis: " + "; ".join(summary_parts) + "." if summary_parts else ""
    
    def _analyze_spatial_distribution(self, detections):
        """Analyze how objects are distributed across the frame"""
        if len(detections) < 2:
            return ""
        
        # Divide frame into zones for analysis
        top_zone = [d for d in detections if d['center'][1] < 0.33]
        bottom_zone = [d for d in detections if d['center'][1] > 0.67]
        center_x_zone = [d for d in detections if 0.33 <= d['center'][0] <= 0.67]
        
        # True center zone (both x and y centered)
        true_center = [d for d in detections if 0.33 <= d['center'][0] <= 0.67 and 
                                                 0.33 <= d['center'][1] <= 0.67]
        
        # Check for clustering patterns
        high_importance = [d for d in detections if d['importance'] > 6]
        
        if len(true_center) > len(detections) * 0.5:
            return "Spatial analysis: Objects concentrated in central viewing area."
        elif len(center_x_zone) > len(detections) * 0.6 and len(bottom_zone) > len(detections) * 0.4:
            return "Spatial analysis: Objects clustered in lower center path."
        elif len(top_zone) > len(detections) * 0.6:
            return "Spatial analysis: Objects primarily in upper field of view."
        elif len(high_importance) > 3:
            return "Spatial analysis: Multiple high-priority objects detected across scene."
        
        return ""
    
    def _check_collision_trajectories(self, moving_objects):
        """Check if any objects are on collision trajectories"""
        if len(moving_objects) < 1:
            return ""
        
        collision_risks = []
        
        for obj in moving_objects:
            # Project trajectory 10 frames ahead
            future_x = obj['center'][0] + (obj['velocity'][0] * 10)
            future_y = obj['center'][1] + (obj['velocity'][1] * 10)
            
            # Check if trajectory leads to center of frame (collision path)
            # Must be in BOTH horizontal AND vertical center zones
            in_center_x = 0.35 <= future_x <= 0.65
            in_center_y = 0.35 <= future_y <= 0.65
            moving_toward_camera = obj['velocity'][1] < -0.003
            
            # Also check current position - if already in center and moving toward camera
            currently_centered_x = 0.4 <= obj['center'][0] <= 0.6
            currently_centered_y = 0.4 <= obj['center'][1] <= 0.6
            
            if ((in_center_x and in_center_y and moving_toward_camera) or 
                (currently_centered_x and currently_centered_y and moving_toward_camera)):
                collision_risks.append(obj['class'])
        
        if collision_risks:
            return f"COLLISION WARNING: {', '.join(collision_risks[:2])} on direct approach trajectory."
        
        return ""
