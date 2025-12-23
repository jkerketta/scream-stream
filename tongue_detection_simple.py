import cv2
import mediapipe as mp
import asyncio
import websockets
import json
import threading
import time

print("🚀 Starting MediaPipe Head Tilt Detection Server...")

mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

connected_clients = set()
position_queue = None
websocket_loop = None

async def register_client(websocket):
    connected_clients.add(websocket)
    print(f"✅ Client connected. Total clients: {len(connected_clients)}")
    try:
        await websocket.wait_closed()
    finally:
        connected_clients.remove(websocket)
        print(f"❌ Client disconnected. Total clients: {len(connected_clients)}")

async def broadcast_head_tilt(position):
    """Broadcast head tilt position to all connected clients"""
    global connected_clients
    if connected_clients:
        message = json.dumps({"head_tilt": position})
        disconnected = set()
        for client in connected_clients.copy(): 
            try:
                await client.send(message)
            except (websockets.exceptions.ConnectionClosed, Exception) as e:
                disconnected.add(client)
        connected_clients -= disconnected

async def broadcast_worker():
    """Worker that broadcasts messages from queue"""
    while True:
        position = await position_queue.get()
        await broadcast_head_tilt(position)
        position_queue.task_done()

async def websocket_server():
    """Start WebSocket server on port 8765"""
    global position_queue
    print("🌐 Starting WebSocket server on ws://localhost:8765")
    position_queue = asyncio.Queue()
    asyncio.create_task(broadcast_worker())
    async with websockets.serve(register_client, "localhost", 8765):
        await asyncio.Future()  

def start_websocket_server():
    """Start WebSocket server in a separate thread"""
    global websocket_loop
    websocket_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(websocket_loop)
    websocket_loop.run_until_complete(websocket_server())

def detect_head_tilt(landmarks, image_width, image_height):
    """
    Detect head tilt/rotation based on MediaPipe landmarks.
    Uses key facial landmarks to calculate head rotation angle.
    """
    try:
        left_eye_outer = landmarks.landmark[33]   
        right_eye_outer = landmarks.landmark[263] 
        
        left_face = landmarks.landmark[234]  
        right_face = landmarks.landmark[454]  
        
        nose_tip = landmarks.landmark[4]
        
        eye_distance = abs(left_eye_outer.x - right_eye_outer.x) * image_width
        
        eye_vertical_diff = (right_eye_outer.y - left_eye_outer.y) * image_height
        
        tilt_ratio = eye_vertical_diff / eye_distance if eye_distance > 0 else 0
        
        tilt_threshold = 0.05 
        
        if tilt_ratio > tilt_threshold:
            return "right"
        elif tilt_ratio < -tilt_threshold:
            return "left"
        else:
            return "center"
            
    except Exception as e:
        print(f"Error detecting head tilt: {e}")
        return "center"

websocket_thread = threading.Thread(target=start_websocket_server, daemon=True)
websocket_thread.start()
print("✅ WebSocket server started. Waiting for clients to connect...")
time.sleep(1)

def open_camera():
    for i in range(3):
        cap = cv2.VideoCapture(i)
        if cap.isOpened():
            print(f"✅ Using camera index {i}")
            return cap
    raise RuntimeError("❌ No working camera found!")

cap = open_camera()

face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=False,
    max_num_faces=1,
    refine_landmarks=True,   
    min_detection_confidence=0.5,
    min_tracking_confidence=0.5
)

print("📹 Starting camera...")
print("👤 Head tilt detection active! Tilt your head left/right to control video.")
print("📺 Camera window should open now. Press 'q' in the window to quit.")
print("")

last_position = None
last_broadcast_time = 0
broadcast_cooldown = 0.3  
frame_count = 0

try:
    while True:
        ret, frame = cap.read()
        if not ret:
            print("⚠️ Failed to read frame from camera")
            time.sleep(0.1)
            continue
        
        frame_count += 1
    
        frame = cv2.flip(frame, 1)
        image_height, image_width, _ = frame.shape
        
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb_frame)
        
        if results.multi_face_landmarks:
            for face_landmarks in results.multi_face_landmarks:
                mp_drawing.draw_landmarks(
                    frame,
                    face_landmarks,
                    mp_face_mesh.FACEMESH_CONTOURS,
                    None,
                    mp_drawing.DrawingSpec(color=(0, 255, 0), thickness=1, circle_radius=1)
                )
                
                head_tilt = detect_head_tilt(face_landmarks, image_width, image_height)
                
                color = (0, 255, 0)  
                if head_tilt == "right":
                    color = (255, 0, 0)  
                elif head_tilt == "left":
                    color = (255, 0, 255)  
                
                cv2.putText(frame, f"Head: {head_tilt.upper()}", 
                           (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1.5, color, 3)
                
                if head_tilt == "right":
                    cv2.putText(frame, "->", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                elif head_tilt == "left":
                    cv2.putText(frame, "<-", (50, 100), cv2.FONT_HERSHEY_SIMPLEX, 1, color, 2)
                
                current_time = time.time()
                if (current_time - last_broadcast_time) > broadcast_cooldown:
                    last_broadcast_time = current_time
                    
                    if head_tilt != last_position:
                        last_position = head_tilt
                        print(f"👤 Head Tilt: {head_tilt.upper()} (Broadcasting to {len(connected_clients)} clients)")
                    
                    if websocket_loop and position_queue:
                        try:
                            asyncio.run_coroutine_threadsafe(position_queue.put(head_tilt), websocket_loop)
                        except Exception as e:
                            print(f"⚠️ Error broadcasting: {e}")
        else:
            if frame_count % 60 == 0:  
                cv2.putText(frame, "No face detected", 
                           (50, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
        
        cv2.imshow('MediaPipe Head Tilt Detection - Press Q to quit', frame)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('q'):
            print("\n🛑 Quit key pressed. Shutting down...")
            break
            
except KeyboardInterrupt:
    print("\n🛑 Interrupted by user. Shutting down...")
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
finally:
    cap.release()
    cv2.destroyAllWindows()
    print("👋 Shutting down...")

