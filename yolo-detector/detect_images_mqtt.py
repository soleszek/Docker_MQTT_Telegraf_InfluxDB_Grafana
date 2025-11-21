# detect_mqtt.py
import os, json, time, cv2
from ultralytics import YOLO
import paho.mqtt.client as mqtt
from datetime import datetime

# --- configuration---
MQTT_BROKER = os.getenv("MQTT_BROKER", "mqtt")   # name of the MQTTbroker container
MQTT_PORT = int(os.getenv("MQTT_PORT", 1883))
MQTT_TOPIC_IN = "cam/new_image"
MQTT_TOPIC_OUT = "traffic/cars"
IMAGES_DIR = "/app/uploads" 
MODEL_PATH = "yolov8n.pt"

vehicle_classes = {"car", "truck", "bus", "motorbike"}

# --- YOLO model initialization ---
model = YOLO(MODEL_PATH)
model.to('cuda')   # 🔹 added CUDA acceleration
print("✅ YOLO model loaded on CUDA")

# --- MQTT: callback on message received ---
def on_message(client, userdata, msg):
    try:
        payload = json.loads(msg.payload.decode())

        Ta = payload.get("Ta")          # Arduino time
        Tstart = int(time.time() * 1000)  # MQTT message received time
        # -----------------------------

        filename = payload.get("file")
        if not filename:
            return
        image_path = os.path.join(IMAGES_DIR, filename)
        if not os.path.exists(image_path):
            print(f"⚠ No image found: {image_path}")
            return

        frame = cv2.imread(image_path)
        height, width, _ = frame.shape

        # Two zones (for now, arbitrary)
        areas = {
            "left":  [(0, height // 2), (width // 2, height)],
            "right": [(width // 2, height // 2), (width, height)]
        }

        # Vehicle detection
        results = model(frame, verbose=False)
        vehicle_counts = {area: 0 for area in areas}

        for box in results[0].boxes:
            cls = results[0].names[int(box.cls)]
            if cls in vehicle_classes:
                x1, y1, x2, y2 = box.xyxy[0]
                cx, cy = int((x1 + x2) / 2), int((y1 + y2) / 2)
                for area_name, rect in areas.items():
                    (x1a, y1a), (x2a, y2a) = rect
                    if x1a <= cx <= x2a and y1a <= cy <= y2a:
                        vehicle_counts[area_name] += 1

        # Duplication of results: 2 zones → 4 traffic lights
        out_json = {
            "timestamp": int(time.time() * 1000),
            "0": vehicle_counts["left"],    # TLS1_IN
            "1": vehicle_counts["right"],   # TLS2_OUT
            "2": vehicle_counts["left"],    # TLS9_IN
            "3": vehicle_counts["right"],   # TLS10_OUT      
            "Ta": Ta,
            "Tstart": Tstart
        }

        client.publish(MQTT_TOPIC_OUT, json.dumps(out_json))
        print(f"📤 Published: {out_json}")

    except Exception as e:
        print(f"❌ Error processing image: {e}")

# --- MQTT client configuration ---
client = mqtt.Client()
client.on_message = on_message

client.connect(MQTT_BROKER, MQTT_PORT)
client.subscribe(MQTT_TOPIC_IN)
print(f"✅ Subscribed to {MQTT_TOPIC_IN} on {MQTT_BROKER}:{MQTT_PORT}")

# --- main loop ---
client.loop_forever()
