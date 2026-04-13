import os
import pandas as pd
import cv2
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, Dense, LSTM, TimeDistributed
from tensorflow.keras.utils import to_categorical
import tensorflow as tf

# Load video links
video_links_file = os.path.join(os.path.dirname(__file__), '..', 'videos', 'video_links.csv')
df = pd.read_csv(video_links_file)

# Create data directory
data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')
os.makedirs(data_dir, exist_ok=True)

def download_video(url, output_path):
    from pytube import YouTube
    import requests
    if 'youtube.com' in url or 'youtu.be' in url:
        yt = YouTube(url)
        stream = yt.streams.filter(progressive=True, file_extension='mp4').first()
        stream.download(output_path=output_path, filename=os.path.basename(url) + '.mp4')
        return os.path.join(output_path, os.path.basename(url) + '.mp4')
    else:
        response = requests.get(url, stream=True)
        filename = os.path.basename(url) + '.mp4'
        with open(os.path.join(output_path, filename), 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        return os.path.join(output_path, filename)

def extract_frames(video_path, num_frames=30):
    cap = cv2.VideoCapture(video_path)
    frames = []
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    step = max(1, total_frames // num_frames)
    for i in range(0, total_frames, step):
        cap.set(cv2.CAP_PROP_POS_FRAMES, i)
        ret, frame = cap.read()
        if ret:
            frame = cv2.resize(frame, (64, 64))
            frames.append(frame)
        if len(frames) >= num_frames:
            break
    cap.release()
    return np.array(frames)

# Download videos and extract frames
X = []
y = []
for idx, row in df.iterrows():
    url = row['Link']
    activity = row['Work Activity']
    try:
        video_path = download_video(url, data_dir)
        frames = extract_frames(video_path, 30)
        if len(frames) == 30:
            X.append(frames)
            y.append(activity)
        print(f"Processed {url}")
    except Exception as e:
        print(f"Failed to process {url}: {e}")

X = np.array(X)
y = np.array(y)

# Encode labels
le = LabelEncoder()
y_encoded = le.fit_transform(y)
y_categorical = to_categorical(y_encoded)

# Split data
X_train, X_test, y_train, y_test = train_test_split(X, y_categorical, test_size=0.2, random_state=42)

# Build model
model = Sequential()
model.add(TimeDistributed(Conv2D(32, (3, 3), activation='relu'), input_shape=(30, 64, 64, 3)))
model.add(TimeDistributed(MaxPooling2D((2, 2))))
model.add(TimeDistributed(Flatten()))
model.add(LSTM(50))
model.add(Dense(len(le.classes_), activation='softmax'))

model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])

# Train model
model.fit(X_train, y_train, epochs=10, validation_data=(X_test, y_test))

# Save model
model.save(os.path.join(data_dir, 'activity_model.h5'))
np.save(os.path.join(data_dir, 'label_encoder.npy'), le.classes_)

print("Training complete.")