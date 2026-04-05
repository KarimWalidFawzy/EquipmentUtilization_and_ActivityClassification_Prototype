# Equipment Utilization & Activity Classification Prototype

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

## 🚀 Setup Instructions

### Prerequisites
* Docker & Docker Compose
* NVIDIA GPU (Optional, for faster inference)
* Python 3.9+ (For local development)

### Quick Start (Docker)
To spin up the entire pipeline (Kafka, Database, CV Service, and UI):

```bash
docker-compose up --build