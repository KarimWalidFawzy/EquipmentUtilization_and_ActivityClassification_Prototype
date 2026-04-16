import json
import os
import time
import datetime
import random

import cv2
import numpy as np
from kafka import KafkaProducer
from kafka.errors import KafkaError
import pandas as pd
import requests
from pytube import YouTube
from tensorflow.keras.models import load_model
import joblib

VIDEO_SOURCE = os.getenv("VIDEO_SOURCE", "/app/data/construction_video.mp4")
KAFKA_BROKER = os.getenv("KAFKA_BROKER", "localhost:9092")
KAFKA_TOPIC = os.getenv("KAFKA_TOPIC", "equipment_status")
EQUIPMENT_ID = os.getenv("EQUIPMENT_ID", "excavator_1")
FRAME_RATE = float(os.getenv("FRAME_RATE", "2.0"))

def download_video(url, output_path):
    if 'youtube.com' in url or 'youtu.be' in url:
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
        stream.download(output_path=output_path, filename='video.mp4')
        return os.path.join(output_path, 'video.mp4')
    else:
        response = requests.get(url, stream=True)
        with open(os.path.join(output_path, 'video.mp4'), 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return os.path.join(output_path, 'video.mp4')

# Check for video links file
video_links_file = os.path.join(os.path.dirname(__file__), '..', 'videos', 'video_links.csv')
if os.path.exists(video_links_file):
    df = pd.read_csv(video_links_file)
    if not df.empty:
        VIDEO_SOURCE = df['Link'].iloc[0]  # Use the first URL

ACTIVE_THRESHOLD = 0.005
HIGH_ACTIVITY_THRESHOLD = 0.04

# Load trained model if available
model_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'activity_model.h5')
label_encoder_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'label_encoder.npy')
if os.path.exists(model_path) and os.path.exists(label_encoder_path):
    model = load_model(model_path)
    label_encoder = np.load(label_encoder_path)
    use_dl_model = True
    print("Loaded trained deep learning model for activity classification.")
else:
    use_dl_model = False
    print("No trained model found, using motion-based classification.")


def create_producer():
    while True:
        try:
            producer = KafkaProducer(
                bootstrap_servers=[KAFKA_BROKER],
                value_serializer=lambda v: json.dumps(v).encode("utf-8"),
                retries=5,
            )
            print(f"Connected to Kafka broker at {KAFKA_BROKER}")
            return producer
        except Exception as exc:
            print(f"Kafka connection failed: {exc}. Retrying in 5 seconds...")
            time.sleep(5)


def open_video_source():
    if VIDEO_SOURCE.startswith('http'):
        # Download video
        data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
        os.makedirs(data_dir, exist_ok=True)
        video_path = download_video(VIDEO_SOURCE, data_dir)
        cap = cv2.VideoCapture(video_path)
    else:
        cap = cv2.VideoCapture(VIDEO_SOURCE)
    
    if cap.isOpened():
        print(f"Using video source: {VIDEO_SOURCE}")
        return cap, False

    cap = cv2.VideoCapture(0)
    if cap.isOpened():
        print("Using local camera as fallback video source.")
        return cap, False

    print("Video source unavailable. Using synthetic sample feed.")
    return None, True


def generate_synthetic_frame(frame_index: int):
    height, width = 480, 640
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    box_w, box_h = 120, 80
    x = int((width - box_w) / 2 + 140 * np.sin(frame_index * 0.16))
    y = int((height - box_h) / 2 + 40 * np.sin(frame_index * 0.07))
    cv2.rectangle(frame, (x, y), (x + box_w, y + box_h), (0, 160, 255), -1)
    cv2.putText(frame, "SIMULATED EQUIPMENT", (12, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    return frame


def classify_activity(motion_ratio: float) -> tuple[str, float]:
    if motion_ratio > HIGH_ACTIVITY_THRESHOLD:
        return "Digging", min(0.98, 0.5 + motion_ratio * 8)
    if motion_ratio > ACTIVE_THRESHOLD:
        return "Loading", min(0.92, 0.45 + motion_ratio * 6)
    return "Waiting", 0.4


def create_payload(state: str, activity: str, confidence: float, utilization: float, active: float, idle: float) -> dict:
    return {
        "timestamp": datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z",
        "equipment_id": EQUIPMENT_ID,
        "state": state,
        "activity": activity,
        "confidence": round(confidence, 2),
        "utilization_percentage": round(utilization, 1),
        "total_active_time": int(active),
        "total_idle_time": int(idle),
    }


def main():
    producer = create_producer()
    capture, synthetic = open_video_source()
    bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=30, detectShadows=True)

    active_time = 0.0
    idle_time = 0.0
    last_time = time.time()
    frame_index = 0
    last_state = "INACTIVE"
    print("CV service started.")

    while True:
        start_time = time.time()
        if synthetic:
            frame = generate_synthetic_frame(frame_index)
            frame_index += 1
        else:
            if not capture.isOpened():
                capture, synthetic = open_video_source()
                continue
            ret, frame = capture.read()
            if not ret:
                capture.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        mask = bg_subtractor.apply(gray)
        _, thresh = cv2.threshold(mask, 200, 255, cv2.THRESH_BINARY)
        motion_area = np.count_nonzero(thresh)
        motion_ratio = motion_area / float(frame.shape[0] * frame.shape[1])

        state = "ACTIVE" if motion_ratio > ACTIVE_THRESHOLD else "INACTIVE"
        activity, confidence = classify_activity(motion_ratio)
        if state == "INACTIVE":
            activity = "Waiting"

        now = time.time()
        interval = max(0.01, now - last_time)
        last_time = now
        if state == "ACTIVE":
            active_time += interval
        else:
            idle_time += interval

        utilization = float(active_time) / max(1.0, active_time + idle_time) * 100.0
        payload = create_payload(state, activity, confidence, utilization, active_time, idle_time)

        try:
            producer.send(KAFKA_TOPIC, payload)
            producer.flush()
            if state != last_state or frame_index % 10 == 0:
                print(f"Sent payload: {payload}")
            last_state = state
        except KafkaError as exc:
            print(f"Failed to send payload to Kafka: {exc}")
            time.sleep(5)
            producer = create_producer()
            continue

        elapsed = time.time() - start_time
        sleep_time = max(0, 1.0 / FRAME_RATE - elapsed)
        time.sleep(sleep_time)


if __name__ == "__main__":
    main()
