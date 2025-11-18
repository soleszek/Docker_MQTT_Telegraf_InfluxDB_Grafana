# --- Czysty obraz Pythona 3.10 ---
FROM python:3.10-slim

WORKDIR /app

# --- biblioteki systemowe wymagane przez OpenCV i PyTorch ---
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgl1 libglib2.0-0 libgomp1 && \
    rm -rf /var/lib/apt/lists/*

# --- instalacja stabilnych wersji PyTorch + CUDA + zależności ---
RUN pip install --no-cache-dir --upgrade pip setuptools wheel && \
    pip install --no-cache-dir torch==2.1.0 torchvision==0.16.0 torchaudio==2.1.0 --index-url https://download.pytorch.org/whl/cu118 && \
    pip install --no-cache-dir numpy==1.26.4 && \
    pip install --no-cache-dir opencv-python-headless==4.8.1.78 && \
    pip install --no-cache-dir ultralytics==8.2.79 paho-mqtt

# --- kopiowanie plików aplikacji ---
COPY detect_images_mqtt.py .
COPY yolov8n.pt .

# --- komenda startowa ---
CMD ["python3", "detect_images_mqtt.py"]