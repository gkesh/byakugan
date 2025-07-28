import cv2
import base64
import requests
import json

# Capture frame from webcam or load image
cap = cv2.VideoCapture(0)
ret, frame = cap.read()
cap.release()

# Or load from file
# frame = cv2.imread('test_image.jpg')

# Encode frame
_, buffer = cv2.imencode('.jpg', frame)
frame_base64 = base64.b64encode(buffer).decode('utf-8')

# Send to server
response = requests.post(
    'http://localhost:5000/process_frame',
    json={'frame': frame_base64}
)

print(json.dumps(response.json(), indent=2))