import requests
import logging
import json

# Ollama configuration (assuming local Ollama server)
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "llama3.2:3b"  # Lightweight model

class NavigationAssistant:
    def __init__(self, context_manager):
        self.context_manager = context_manager
        
    
    def get_navigation_guidance(self, scene_description, detections):
        """Get navigation guidance from local LLM with temporal context"""
        # Get temporal context
        temporal_context = self.context_manager.get_context_for_prompt()
        trend_analysis = self.context_manager.get_trend_analysis()
        
        # Build enhanced prompt with context
        prompt = self._build_contextual_prompt(scene_description, temporal_context, trend_analysis, json.dumps(detections))
        
        payload = {
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,
                "top_p": 0.9,
                "max_tokens": 120
            }
        }
        
        try:
            response = requests.post(OLLAMA_URL, json=payload, timeout=3)
            if response.status_code == 200:
                result = response.json()
                guidance = result.get('response', 'Unable to generate guidance at this time.')
                
                # Store this session in context manager
                self.context_manager.add_navigation_session(scene_description, guidance, detections)
                
                return guidance
            else:
                return "Navigation system temporarily unavailable."
        except requests.exceptions.RequestException as e:
            logging.error(f"LLM request failed: {e}")
            return "Please proceed with caution and use your best judgment."
    
    def _build_contextual_prompt(self, current_scene, temporal_context, trend_analysis, details = None):
        """Build a contextual prompt with temporal awareness"""
        base_prompt = f"""You are a obstacle avoidance assisstant someone who is visually impaired and cannot see anything. You provide short, clear, and casual directions on how to safely navigate around obstacles. And do not greet the user, just give instructions.

{temporal_context}

Current scene: {current_scene}"""

        if details:
            base_prompt += f"\n\n Here is a detailed list of items on in front of the user, use this to formulate better instructions. \n {details}"
        
        # Add trend-based context if available
        if trend_analysis:
            trend_context = ""
            
            if trend_analysis['recurring_obstacles']:
                recurring = ", ".join(trend_analysis['recurring_obstacles'])
                trend_context += f"\nNote: You've been seeing {recurring} repeatedly in this area. "
            
            if trend_analysis['danger_trend'] == 'increasing':
                trend_context += "The situation seems to be getting more complex. "
            elif trend_analysis['danger_trend'] == 'decreasing':
                trend_context += "The path seems to be getting clearer. "
            
            if trend_context:
                base_prompt += trend_context
        
        base_prompt += """\n\nProvide navigation advice that:
1. Acknowledges any changes from previous guidance if relevant
2. Is encouraging and supportive
3. Is single or two short sentences maximum
4. Focuses on immediate next steps
5. If there is immediate obstacle, just say 'stop'

Most importantly, you are not helping them get to some place, you are helping them avoid obstacles on the way.

Do not repeat the same information as the "Recent Navigation Context", if there is no scene change give more dynamic response."""
        
        return base_prompt
