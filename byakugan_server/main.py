from flask import Flask, request, jsonify
import cv2
import numpy as np
import base64
from datetime import datetime
import logging

from agents.temporal_ctx_manager import TemporalContextManager
from agents.navigation_assistant import NavigationAssistant
from agents.object_detector import AdvancedObjectDetector as ObjectDetector
from agents.scene_describer import AdvancedSceneDescriber as SceneDescriber


app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Object importance weights for navigation assistance
OBSTACLE_WEIGHTS = {
    # Critical obstacles (highest priority)
    'person': 10,
    'car': 9,
    'truck': 9,
    'bus': 9,
    'motorcycle': 8,
    'bicycle': 7,
    
    # Structural obstacles
    'stop sign': 8,
    'traffic light': 7,
    'fire hydrant': 6,
    'bench': 5,
    'chair': 4,
    'dining table': 4,
    
    # Ground level obstacles
    'suitcase': 6,
    'backpack': 4,
    'handbag': 3,
    'bottle': 3,
    'cup': 2,
    
    # Animals
    'dog': 7,
    'cat': 5,
    'bird': 2,
    
    # Default weight for unspecified objects
    'default': 3
}


# Initialize temporal context manager
context_manager = TemporalContextManager(max_history=3) # type: ignore


# Initialize components
detector = ObjectDetector(weights=OBSTACLE_WEIGHTS)
describer = SceneDescriber()
navigator = NavigationAssistant(context_manager=context_manager)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().isoformat()})

@app.route('/process_frame', methods=['POST'])
def process_frame():
    """Main endpoint to process video frame"""
    try:
        # Get base64 encoded frame from request
        data = request.json
        if 'frame' not in data: # type: ignore
            return jsonify({'error': 'No frame data provided'}), 400
        
        # Decode base64 frame
        frame_data = base64.b64decode(data['frame']) # type: ignore
        nparr = np.frombuffer(frame_data, np.uint8)
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if frame is None:
            return jsonify({'error': 'Invalid frame data'}), 400
        
        # Process frame
        detections = detector.detect_objects(frame)
        scene_description = describer.create_scene_description(detections, frame.shape)
        navigation_guidance = navigator.get_navigation_guidance(scene_description, detections)
        
        # Prepare response
        response_data = {
            'timestamp': datetime.now().isoformat(),
            'detections_count': len(detections),
            'scene_description': scene_description,
            'navigation_guidance': navigation_guidance,
            'detections': detections[:5],  # Return top 5 most important detections
            'context_info': {
                'sessions_in_memory': len(context_manager.navigation_history),
                'trend_analysis': context_manager.get_trend_analysis()
            }
        }
        
        return jsonify(response_data)
    
    except Exception as e:
        logging.error(f"Error processing frame: {e}")
        return jsonify({'error': 'Frame processing failed'}), 500

@app.route('/context/history', methods=['GET'])
def get_navigation_history():
    """Get navigation history for debugging/monitoring"""
    try:
        history = list(context_manager.navigation_history)
        trend_analysis = context_manager.get_trend_analysis()
        
        return jsonify({
            'history': history,
            'trend_analysis': trend_analysis,
            'total_sessions': len(history)
        })
    
    except Exception as e:
        logging.error(f"Error retrieving history: {e}")
        return jsonify({'error': 'Failed to retrieve history'}), 500

@app.route('/context/clear', methods=['POST'])
def clear_navigation_history():
    """Clear navigation history"""
    try:
        context_manager.clear_history()
        return jsonify({'message': 'Navigation history cleared successfully'})
    
    except Exception as e:
        logging.error(f"Error clearing history: {e}")
        return jsonify({'error': 'Failed to clear history'}), 500

@app.route('/context/stats', methods=['GET'])
def get_context_stats():
    """Get context statistics"""
    try:
        trend_analysis = context_manager.get_trend_analysis()
        temporal_context = context_manager.get_context_for_prompt()
        
        return jsonify({
            'sessions_count': len(context_manager.navigation_history),
            'trend_analysis': trend_analysis,
            'context_preview': temporal_context[:200] + "..." if len(temporal_context) > 200 else temporal_context
        })
    
    except Exception as e:
        logging.error(f"Error getting context stats: {e}")
        return jsonify({'error': 'Failed to get context stats'}), 500

@app.route('/weights', methods=['PUT'])
def update_weights():
    """Update obstacle importance weights"""
    try:
        data = request.json
        if 'weights' not in data: # type: ignore
            return jsonify({'error': 'No weights data provided'}), 400
        
        # Update weights
        for obj_class, weight in data['weights'].items(): # type: ignore
            if isinstance(weight, (int, float)) and 0 <= weight <= 10:
                OBSTACLE_WEIGHTS[obj_class] = weight # type: ignore
        
        # Recreating object detector
        detector = ObjectDetector(weights=OBSTACLE_WEIGHTS)
        
        return jsonify({'message': 'Weights updated successfully', 'current_weights': OBSTACLE_WEIGHTS})
    
    except Exception as e:
        logging.error(f"Error updating weights: {e}")
        return jsonify({'error': 'Weight update failed'}), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Make sure Ollama is running with the model loaded!")
    print("Test with: curl -X GET http://localhost:5000/health")
    app.run(debug=True, host='0.0.0.0', port=5000, threaded=True)
