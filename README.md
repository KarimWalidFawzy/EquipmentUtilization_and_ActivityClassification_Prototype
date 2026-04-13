# Technical Assessment: Equipment Utilization & Activity Classification Prototype

This project is a real-time, microservices-based computer vision pipeline designed to track construction equipment utilization. It distinguishes between **ACTIVE** and **INACTIVE** states, classifies specific work activities, and calculates efficiency metrics using a distributed architecture. The system now includes deep learning model training using videos extracted from online sources.

---

## 🏗️ Architecture Overview

The system is designed for scalability using a decoupled microservices approach:

1.  **CV Inference Service**: 
    * **Video Source**: Reads video links from `videos/video_links.csv` and downloads videos from online sources (YouTube, Pexels, etc.).
    * **Motion Analysis**: Implements background subtraction for motion detection to identify "Active" states.
    * **Activity Classifier**: Classifies activities based on motion thresholds (Digging, Loading, Waiting).
    * **Deep Learning Training**: A separate training script extracts frames from downloaded videos and trains a CNN-LSTM model for activity classification.
2.  **Message Broker (Apache Kafka)**: 
    * Streams real-time JSON payloads from the CV engine to the backend and UI.
3.  **Data Sink**: 
    * Persists metrics into **PostgreSQL/TimescaleDB** for time-series analysis.
4.  **User Interface**: 
    * A **Streamlit** dashboard displaying the live annotated feed, machine status, and utilization percentages.

---

## 🧠 Technical Write-up & Design Decisions

### 1. Video Data Extraction
**Problem**: Need training data from various online sources for deep learning model training.

**Solution**: The system reads video links from a CSV file and automatically downloads videos using appropriate libraries (pytube for YouTube, requests for direct downloads).

### 2. Deep Learning Model Training
**Approach**: A CNN-LSTM model is trained on extracted video frames.
* **Frame Extraction**: Videos are sampled to extract 30 frames each, resized to 64x64.
* **Model Architecture**: Convolutional layers for spatial features, followed by LSTM for temporal analysis.
* **Training Data**: Uses "Work Activity" labels from the CSV for supervised learning.

### 3. Activity Classification
Specific activities are classified using motion-based heuristics in real-time inference.
* **Digging**: High motion ratio.
* **Loading**: Moderate motion ratio.
* **Waiting**: Low motion ratio.

---

## 📡 Expected Kafka Payload Format

The CV microservice outputs a JSON payload to Kafka to support state, activity, and time analysis. An example payload is as follows:

```json
{
  "timestamp": "2023-10-01T12:00:00Z",
  "equipment_id": "excavator_1",
  "state": "ACTIVE",
  "activity": "Digging",
  "confidence": 0.95,
  "utilization_percentage": 75.5,
  "total_active_time": 4500,
  "total_idle_time": 1500
}
```

This payload includes:
- `timestamp`: ISO 8601 formatted timestamp of the analysis.
- `equipment_id`: Unique identifier for the detected equipment.
- `state`: Current state ("ACTIVE" or "INACTIVE").
- `activity`: Classified activity ("Digging", "Loading", "Waiting").
- `confidence`: Confidence score for the classification (0-1).
- `utilization_percentage`: Overall utilization percentage.
- `total_active_time`: Cumulative active time in seconds.
- `total_idle_time`: Cumulative idle time in seconds.

---

## 🚀 Setup Instructions

### Prerequisites
* Docker & Docker Compose
* Python 3.9+ (For local development)

### Quick Start (Docker)
To spin up the entire pipeline (Kafka, Database, CV Service, and UI):

```bash
docker-compose up --build
```
This will start all services and the Streamlit dashboard will be accessible at `http://localhost:8501`.

### Local Development
1. **CV Inference Service**:
   * Navigate to the `cv_service` directory.
   * Install dependencies: `pip install -r requirements.txt`
   * Run the service: `python cv_service.py`
   * The service reads from `videos/video_links.csv` and downloads the first video for inference.
2. **Training the Deep Learning Model**:
   * In the `cv_service` directory, run: `python train.py`
   * This downloads all videos from the CSV, extracts frames, and trains the model.
   * The trained model is saved to `data/activity_model.h5`.
3. **Streamlit Dashboard**:
    * Navigate to the `ui` directory.
    * Install dependencies: `pip install -r requirements.txt`
    * Run the dashboard: `streamlit run ui.py`
4. **Kafka & Database**:
    * Use Docker Compose to start Kafka and PostgreSQL: `docker-compose up kafka db`

---
## 📊 Metrics & Evaluation
* **Utilization Rate**: Percentage of time the machine is classified as "Active" over a given period.
* **Activity Breakdown**: Time spent in each activity (Digging, Loading, Waiting).
* **Accuracy**: Evaluated using a labeled dataset of construction footage, comparing predicted states/activities against ground truth annotations.
* **Latency**: Time taken from frame capture to activity classification, aiming for sub-second performance.
---
## 🎥 Demo Video/GIF

A visual demonstration of the working solution is available in the `demo/` directory:
- `demo_video.mp4`: Full demo showing real-time processing of construction equipment video.
- `demo.gif`: Animated GIF highlighting key features (bounding boxes, status updates, utilization dashboard).

The demo illustrates:
- Live video feed with equipment detection and bounding boxes.
- Real-time ACTIVE/INACTIVE status updates.
- Activity classification transitions.
- Utilization percentage calculations updating in real-time.

---

## 🛠️ Future Enhancements
* **Edge Deployment**: Optimize the CV model for edge devices (e.g., NVIDIA Jetson) to reduce latency and bandwidth usage.
* **Multi-Camera Fusion**: Integrate data from multiple camera angles for improved accuracy in activity classification.
* **Predictive Analytics**: Use historical utilization data to predict maintenance needs or optimize scheduling.
* **Integration with BIM**: Link real-time equipment data with Building Information Modeling (BIM) systems for enhanced project management.
---
