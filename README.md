# Technical Assessment: Equipment Utilization & Activity Classification Prototype

This project is a real-time, microservices-based computer vision pipeline designed to track construction equipment utilization. It distinguishes between **ACTIVE** and **INACTIVE** states, classifies specific work activities, and calculates efficiency metrics using a distributed architecture.

---

## 🏗️ Architecture Overview

The system is designed for scalability using a decoupled microservices approach:

1.  **CV Inference Service**: 
    * **Detection & Tracking**: Uses YOLOv8/v10 for equipment localization.
    * **Motion Analysis**: Implements region-based motion detection to identify "Active" states even when the machine's base is stationary.
    * **Activity Classifier**: A temporal analysis module to identify Digging, Swinging, Loading, and Dumping.
2.  **Message Broker (Apache Kafka)**: 
    * Streams real-time JSON payloads from the CV engine to the backend and UI.
3.  **Data Sink**: 
    * Persists metrics into **PostgreSQL/TimescaleDB** for time-series analysis.
4.  **User Interface**: 
    * A **Streamlit** dashboard displaying the live annotated feed, machine status, and utilization percentages.

---

## 🧠 Technical Write-up & Design Decisions

### 1. The Articulated Equipment Challenge
**Problem**: Standard bounding box tracking often marks an excavator as "Inactive" if the tracks aren't moving, even if the arm is digging.

**Solution**: This prototype uses **Mask-based Motion Analysis**. 
* Instead of tracking the center of a bounding box, we apply **Optical Flow (Farneback)** or **Background Subtraction** specifically within the instance segmentation mask of the machine.
* By calculating the mean magnitude of motion vectors within the mask, we can detect articulated movement (arm/bucket) regardless of chassis stationarity. 
* **Trade-off**: While instance segmentation is more computationally expensive than simple bounding boxes, it is necessary for high-accuracy activity classification in construction.

### 2. Activity Classification
Specific activities (Digging, Swinging, etc.) are classified using a **State Machine + Temporal Windows**.
* **Digging**: Detected by a combination of arm-region motion and a downward trajectory of the bucket keypoint.
* **Swinging**: Identified by the horizontal expansion/contraction of the mask or tracking the rotation of the upper carriage relative to the tracks.
* **Waiting**: Categorized by a lack of significant motion within the mask for a duration exceeding 3 seconds.

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
- `activity`: Classified activity ("Digging", "Swinging/Loading", "Dumping", "Waiting").
- `confidence`: Confidence score for the classification (0-1).
- `utilization_percentage`: Overall utilization percentage.
- `total_active_time`: Cumulative active time in seconds.
- `total_idle_time`: Cumulative idle time in seconds.

---

## 🚀 Setup Instructions

### Prerequisites
* Docker & Docker Compose
* NVIDIA GPU (Optional, for faster inference)
* Python 3.9+ (For local development)

### Quick Start (Docker)
To spin up the entire pipeline (Kafka, Database, CV Service, and UI):

```bash
docker-compose -f docker-composer.yml up --build
```
This will start all services and the Streamlit dashboard will be accessible at `http://localhost:8501`.
### Local Development
1. **CV Inference Service**:
   * Navigate to the `cv_service` directory.
   * Install dependencies: `pip install -r requirements.txt`
   * Run the service: `python app.py`
2. **Streamlit Dashboard**:
    * Navigate to the `ui` directory.
    * Install dependencies: `pip install -r requirements.txt`
    * Run the dashboard: `streamlit run dashboard.py`
3. **Kafka & Database**:
    * Use Docker Compose to start Kafka and PostgreSQL: `docker-compose -f docker-composer.yml up kafka db`
---
## 📊 Metrics & Evaluation
* **Utilization Rate**: Percentage of time the machine is classified as "Active" over a given period.
* **Activity Breakdown**: Time spent in each activity (Digging, Swinging, etc.).
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
