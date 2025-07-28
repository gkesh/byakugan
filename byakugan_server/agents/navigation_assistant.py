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
        # Get temporal context
        temporal_context = self.context_manager.get_context_for_prompt()
        trend_analysis = self.context_manager.get_trend_analysis()
        
        # Build enhanced prompt with context
        prompt = self._build_contextual_prompt(scene_description, temporal_context, trend_analysis)
        
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
        base_prompt = f"""You are a obstacle avoidance assisstant for someone who is visually impaired and cannot see anything. You provide short, clear, and casual directions on how to safely navigate around obstacles. And do not greet the user, just give instructions.

IMPORTANT!! - Remember the person using this app is blind, so do not use phrases like:
- Keep an eye out
- Look out
- Take a look
- See

Instead use phrases like:
- Keep an ear out
- Try and listen for
- Listen

Be sensitive

{temporal_context}

Remember the context provided above are past instructions only to be used as reference to give the conversation more flavor. Do not depend on it for navigation. Make sure to avoid repeating phrases and sentences that you have already used based on the context information provided above, do not be robotic.

Current scene: {current_scene}"""
        
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

Some things to keep in mind when generating instructions.
1. If there is immediate obstacle, tell the person to be careful.
2. If the obstacle is not too critical, just ask the user to proceed slowly.
3. If and only if the situation seems too complex and chaotic, gently tell them to stop and reassess.

Most importantly, you are not helping them get to some place, you are helping them avoid obstacles on the way.

Do not repeat the same information as the "Recent Navigation Context", if there is no scene change give more dynamic response."""
        
        return base_prompt
