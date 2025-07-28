#!/usr/bin/env python3
"""
Test script to demonstrate temporal context functionality
Run this after starting the Flask server to see how context memory works
"""

import requests
import json
import base64
import cv2
import time
from datetime import datetime

SERVER_URL = "http://localhost:5000"

def create_test_frame():
    """Create a simple test frame (or use webcam)"""
    # Create a simple test image with text
    import numpy as np
    
    frame = np.ones((480, 640, 3), dtype=np.uint8) * 255  # White background
    cv2.putText(frame, "TEST FRAME", (200, 240), cv2.FONT_HERSHEY_SIMPLEX, 2, (0, 0, 0), 3)
    
    return frame

def send_frame_to_server(frame):
    """Send frame to server and return response"""
    _, buffer = cv2.imencode('.jpg', frame)
    frame_base64 = base64.b64encode(buffer).decode('utf-8')
    
    try:
        response = requests.post(
            f'{SERVER_URL}/process_frame',
            json={'frame': frame_base64},
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error: HTTP {response.status_code}")
            return None
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        return None

def get_context_history():
    """Get navigation history from server"""
    try:
        response = requests.get(f'{SERVER_URL}/context/history')
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting history: HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Failed to get history: {e}")
        return None

def get_context_stats():
    """Get context statistics from server"""
    try:
        response = requests.get(f'{SERVER_URL}/context/stats')
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error getting stats: HTTP {response.status_code}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Failed to get stats: {e}")
        return None

def clear_context():
    """Clear navigation context"""
    try:
        response = requests.post(f'{SERVER_URL}/context/clear')
        if response.status_code == 200:
            print("✅ Context cleared successfully")
            return True
        else:
            print(f"Error clearing context: HTTP {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"Failed to clear context: {e}")
        return False

def check_server_health():
    """Check if server is running"""
    try:
        response = requests.get(f'{SERVER_URL}/health', timeout=5)
        return response.status_code == 200
    except:
        return False

def simulate_navigation_sequence():
    """Simulate a sequence of navigation requests to demonstrate temporal context"""
    print("🚀 Starting Temporal Context Demonstration")
    print("=" * 50)
    
    # Clear any existing context
    clear_context()
    
    # Simulate different scenarios
    scenarios = [
        {
            "description": "Walking down a clear hallway",
            "simulated_objects": []
        },
        {
            "description": "Person appears ahead",
            "simulated_objects": ["person"]
        },
        {
            "description": "Person still there, now with a chair",
            "simulated_objects": ["person", "chair"]
        },
        {
            "description": "Person moved, chair remains",
            "simulated_objects": ["chair"]
        }
    ]
    
    for i, scenario in enumerate(scenarios, 1):
        print(f"\n🎬 Scenario {i}: {scenario['description']}")
        print("-" * 30)

if __name__ == '__main__':
    simulate_navigation_sequence()