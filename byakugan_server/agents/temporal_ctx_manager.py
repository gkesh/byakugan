from collections import deque
from datetime import datetime
import threading

class TemporalContextManager:
    def __init__(self, max_history=3):
        self.max_history = max_history
        self.navigation_history = deque(maxlen=max_history)
        self._lock = threading.Lock()

    def add_navigation_session(self, scene_description, navigation_guidance, detections):
        """Add a new navigation session to history"""
        with self._lock:
            session = {
                'timestamp': datetime.now().isoformat(),
                'scene_description': scene_description,
                'navigation_guidance': navigation_guidance,
                'key_obstacles': [d['class'] for d in detections[:3]],  # Top 3 obstacles
                'critical_count': len([d for d in detections if d['importance'] >= 8])
            }
            self.navigation_history.append(session)

    def get_context_for_prompt(self):
        """Get formatted context for LLM prompt"""
        with self._lock:
            if not self.navigation_history:
                return "This is the first navigation request."
            
            context_parts = []
            for i, session in enumerate(self.navigation_history):
                time_ref = f"{len(self.navigation_history) - i} moments ago"
                if i == len(self.navigation_history) - 1:
                    time_ref = "just now"
                elif i == len(self.navigation_history) - 2:
                    time_ref = "previously"
                
                context_parts.append(
                    f"{time_ref.capitalize()}: {session['scene_description']} "
                    f"(Guidance given: {session['navigation_guidance']})"
                )
            
            return "Recent navigation context:\n" + "\n".join(context_parts)

    def get_trend_analysis(self):
        """Analyze trends in recent navigation history"""
        with self._lock:
            if len(self.navigation_history) < 2:
                return None
            
            recent_obstacles = []
            critical_trend = []
            
            for session in self.navigation_history:
                recent_obstacles.extend(session['key_obstacles'])
                critical_trend.append(session['critical_count'])
            
            # Check for recurring obstacles
            obstacle_counts = {}
            for obstacle in recent_obstacles:
                obstacle_counts[obstacle] = obstacle_counts.get(obstacle, 0) + 1
            
            recurring = [obs for obs, count in obstacle_counts.items() if count > 1]
            
            # Check if situation is getting more/less dangerous
            danger_trend = "stable"
            if len(critical_trend) >= 2:
                if critical_trend[-1] > critical_trend[-2]:
                    danger_trend = "increasing"
                elif critical_trend[-1] < critical_trend[-2]:
                    danger_trend = "decreasing"
            
            return {
                'recurring_obstacles': recurring,
                'danger_trend': danger_trend,
                'total_sessions': len(self.navigation_history)
            }

    def clear_history(self):
        """Clear navigation history"""
        with self._lock:
            self.navigation_history.clear()