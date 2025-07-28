import numpy as np

class SceneDescriber:
    def create_scene_description(self, detections):
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
        if not obstacles:
            return ""
        
        descriptions = []
        for obs in obstacles:
            size_desc = "large" if obs['size'][0] * obs['size'][1] > 0.1 else "small"
            desc = f"{size_desc} {obs['class']} in the {obs['position_desc']} area"
            descriptions.append(desc)
        
        priority_text = f"{priority_level} ALERT: " if priority_level == "CRITICAL" else ""
        return f"{priority_text}Detected {', '.join(descriptions)}."
