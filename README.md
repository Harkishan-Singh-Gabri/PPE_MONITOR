# VigilAI — AI-Based PPE & Posture Monitoring System

> Real-time workplace safety monitoring using computer vision and generative AI. Detects PPE violations, tracks workers, validates fall incidents, and provides an intelligent safety chatbot — all from a live camera feed.

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [System Architecture](#system-architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Configuration](#configuration)
- [Usage](#usage)
- [Dashboard](#dashboard)
- [Model Training](#model-training)
- [Module Reference](#module-reference)
- [Pipeline Metrics](#pipeline-metrics)

---

## Overview

VigilAI is a modular, production-grade safety monitoring system for construction and industrial environments. It processes live video feeds frame-by-frame through a multi-stage AI pipeline — detecting PPE violations, tracking individual workers with persistent IDs, analyzing posture risk, and validating fall incidents using a vision-language model.

All events are logged to a PostgreSQL database and visualized through a 5-page Streamlit dashboard with an embedded AI safety chatbot.

---

## Features

| Feature | Description |
|---|---|
| **PPE Detection** | Detects 14 classes including Hardhat, Vest, Gloves, Goggles, Mask and their violation counterparts |
| **Worker Tracking** | Centroid-based tracker assigns persistent IDs (W-01, W-02...) across frames |
| **Pose Estimation** | YOLOv8-Pose detects 17 body keypoints per person simultaneously |
| **Posture Analysis** | Joint angle math scores ergonomic risk (LOW / MEDIUM / HIGH) per worker |
| **Fall Detection** | 2-condition check (velocity + horizontal body) triggers Groq vision validation |
| **Groq Validation** | LLaMA-4 Vision confirms falls as FALL_CONFIRMED / FALSE_ALARM / UNCERTAIN |
| **Silent Surveillance** | System operates silently — only alerts on CRITICAL and HIGH events |
| **Violation Persistence** | Violation must appear in N consecutive frames before alerting |
| **Multilingual Alerts** | On-screen alerts translated via deep-translator |
| **DB Logging** | Violations, alerts, and worker sessions logged asynchronously to PostgreSQL |
| **Safety Chatbot** | Natural language queries over violation DB via Groq LLaMA |
| **Streamlit Dashboard** | 5-page UI — live feed, analytics, violations table, chatbot |

---

## System Architecture

```
Camera Feed (webcam / video file)
        ↓
[VideoStream] — frame reading, resolution normalization
        ↓
[PPEDetector — YOLOv8] — 14-class PPE and violation detection
        ↓
[WorkerTracker — Centroid] — persistent worker ID assignment
        ↓
[PoseEstimator — YOLOv8-Pose] — 17 keypoint detection per person
        ↓
[PostureAnalyzer] — joint angles, risk scoring, fall detection
        ↓
[ViolationTracker] — N-frame persistence filter
        ↓
[AlertEngine] — cooldown, severity, translation
        ↓
[Groq Vision API] — async fall validation (background thread)
        ↓
[PostgreSQL] — async violation/alert/worker logging
        ↓
[Streamlit Dashboard] — live feed, analytics, chatbot
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| PPE Detection | YOLOv8 (Ultralytics) — custom trained |
| Pose Estimation | YOLOv8n-Pose |
| Worker Tracking | Custom centroid tracker with Hungarian algorithm (scipy) |
| Fall Validation | Groq API — LLaMA-4 Scout 17B Vision |
| Safety Chatbot | Groq API — LLaMA-3.3 70B Versatile |
| Database | PostgreSQL + SQLAlchemy ORM |
| Dashboard | Streamlit + Plotly |
| Translation | deep-translator (Google Translate) |
| Environment | Python 3.10, NVIDIA CUDA |

---

## Project Structure

```
ppe-monitor/
│
├── config/
│   └── settings.yaml           # all configuration — never hardcode values
│
├── detection/
│   ├── ppe_detector.py         # YOLOv8 inference, bounding boxes
│   ├── pose_estimator.py       # YOLOv8-Pose keypoint extraction
│   ├── posture_analyzer.py     # joint angles, risk scoring, fall detection
│   ├── violation_tracker.py    # N-frame persistence filter
│   └── train.py                # model training script
│
├── tracking/
│   └── tracker.py              # centroid-based persistent worker tracking
│
├── alerts/
│   ├── alert_engine.py         # violation rules, cooldown, Groq integration
│   └── translator.py           # multilingual alert translation
│
├── genai/
│   ├── posture_validator.py    # async Groq vision fall validation
│   └── chatbot.py              # NL → SQL → Groq safety chatbot
│
├── db/
│   ├── models.py               # SQLAlchemy table definitions
│   ├── database.py             # engine, session factory
│   └── crud.py                 # read/write operations
│
├── api/
│   └── pipeline.py             # unified pipeline — integrates all modules
│
├── dashboard/
│   ├── app.py                  # Streamlit entry point + sidebar + CSS
│   └── pages/
│       ├── home.py             # overview dashboard + embedded chatbot
│       ├── live_feed.py        # live video feed + real-time alerts
│       ├── analytics.py        # charts and trends
│       ├── violations.py       # filterable violations table + CSV export
│       └── chatbot.py          # full-page safety chatbot
│
├── utils/
│   ├── config_loader.py        # YAML config + .env loader
│   ├── logger.py               # Loguru setup — colored terminal + file rotation
│   ├── math_utils.py           # angle calculation, midpoint, visibility check
│   └── video_stream.py         # OpenCV camera/video abstraction
│
├── models/                     # YOLOv8 weights (.pt files)
├── dataset/                    # training data (gitignored)
├── reports/                    # violation snapshots (gitignored)
├── logs/                       # log files (gitignored)
│
├── .env                        # secrets — never commit
├── .env.example                # template for secrets
├── requirements.txt
├── environment.yml
└── README.md
```

---

## Setup & Installation

### Prerequisites
- Python 3.10
- NVIDIA GPU with CUDA (recommended)
- PostgreSQL installed and running
- Conda (recommended) or virtualenv

### 1. Clone the repository
```bash
git clone https://github.com/yourname/ppe-monitor.git
cd ppe-monitor
```

### 2. Create conda environment
```bash
conda create -n ppe-monitor python=3.10 -y
conda activate ppe-monitor
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set up PostgreSQL
```bash
# connect as postgres superuser
psql -U postgres

# create user and database
CREATE USER ppeuser WITH PASSWORD 'ppepass';
CREATE DATABASE ppemonitor OWNER ppeuser;
\q
```

### 5. Configure environment variables
```bash
cp .env.example .env
```

Edit `.env`:
```env
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://ppeuser:ppepass@localhost:5432/ppemonitor
```

Get a free Groq API key at: https://console.groq.com

### 6. Initialize database
```bash
python -m db.database
```

### 7. Download or train the model

**Option A — Use your trained weights:**
Place `best_ppe.pt` in the `models/` folder.

**Option B — Train from scratch:**
```bash
# place dataset in dataset/ folder with data.yaml
python -m detection.train
cp models/ppe_training/weights/best.pt models/best_ppe.pt
```

### 8. Verify CUDA
```bash
python -c "import torch; print('CUDA:', torch.cuda.is_available()); print('GPU:', torch.cuda.get_device_name(0))"
```

---

## Configuration

All system behavior is controlled from `config/settings.yaml`. Key parameters:

```yaml
camera:
  source: 0                          # 0 = webcam, or video file path
  resolution: [1280, 720]

detection:
  model_path: models/best_ppe.pt
  confidence_threshold: 0.35         # lower = more detections
  violation_confidence_threshold: 0.65  # strict for violations only
  violation_persistence_frames: 8    # N frames before alert fires

tracker:
  max_age: 45                        # frames before lost track deleted
  
fall_detection:
  velocity_threshold: 0.40           # raise to reduce false falls
  horizontal_threshold: 55

alerts:
  cooldown_sec: 15                   # seconds between same alert repeating
  language: en                       # en, hi, ta, te, bn, mr

pipeline:
  yolo_frame_skip: 2                 # run YOLO every N frames
  pose_frame_skip: 3                 # run pose every N frames
```

---

## Usage

### Run the full dashboard
```bash
streamlit run dashboard/app.py
```

### Run pipeline standalone (OpenCV window)
```bash
python -m api.pipeline
```

### Run individual modules for testing
```bash
python -m detection.ppe_detector       # PPE detection only
python -m detection.pose_estimator     # pose estimation only
python -m tracking.tracker             # worker tracking only
python -m genai.chatbot                # chatbot CLI test
```

### Reset all data
```bash
python -m utils.reset_data
```

---

## Dashboard

The Streamlit dashboard has 5 pages:

| Page | Description |
|---|---|
| **Home** | Metric cards, violations chart, top violations, recent alerts, embedded chatbot |
| **Live Detection** | Upload video or use webcam, live annotated feed, real-time metrics and alerts |
| **Analytics** | Violations over time, by type, by worker, severity distribution |
| **Violations** | Full filterable table with severity/worker/type filters, CSV export |
| **Chatbot** | Full-page natural language interface to violation database |

### Chatbot example queries
```
"How many violations happened today?"
"Which worker had the most violations?"
"Were there any falls detected?"
"Show me NO-Hardhat violations"
"What is today's compliance rate?"
"Violations in the last hour?"
```

---

## Model Training

The PPE model was trained on a custom 14-class dataset:

**Classes:** `Fall-Detected`, `Gloves`, `Goggles`, `Hardhat`, `Ladder`, `Mask`, `NO-Gloves`, `NO-Goggles`, `NO-Hardhat`, `NO-Mask`, `NO-Safety Vest`, `Person`, `Safety Cone`, `Safety Vest`

**Training results (50 epochs, YOLOv8n):**

| Metric | Value |
|---|---|
| Overall mAP50 | 76.4% |
| Goggles | 96.2% |
| NO-Goggles | 94.0% |
| Gloves | 94.3% |
| Hardhat | 89.7% |
| Fall-Detected | 82.5% |
| NO-Hardhat | 73.7% |

To retrain:
```bash
python -m detection.train
```

---

## Module Reference

| Module | Responsibility | Key Output |
|---|---|---|
| `utils/config_loader.py` | Loads `settings.yaml` and `.env` | Config dict, env secrets |
| `utils/logger.py` | Loguru — colored terminal + file rotation | `log` instance |
| `utils/video_stream.py` | OpenCV frame reader | BGR numpy frames |
| `utils/math_utils.py` | Angle, midpoint, visibility geometry | Float angles |
| `detection/ppe_detector.py` | YOLOv8 inference | Detections list |
| `detection/pose_estimator.py` | YOLOv8-Pose keypoints | Landmarks per person |
| `detection/posture_analyzer.py` | Risk scoring + fall detection | Risk level, fall bool |
| `detection/violation_tracker.py` | N-frame persistence | Confirmed detections |
| `tracking/tracker.py` | Centroid matching + Hungarian | Worker IDs + bboxes |
| `alerts/alert_engine.py` | Rules, cooldown, Groq integration | Alerts list |
| `alerts/translator.py` | Google Translate wrapper | Translated string |
| `genai/posture_validator.py` | Async Groq vision fall validator | FALL_CONFIRMED / FALSE_ALARM / UNCERTAIN |
| `genai/chatbot.py` | NL → SQL → Groq summarizer | Plain English answer |
| `db/models.py` | SQLAlchemy ORM table definitions | — |
| `db/database.py` | Engine + session factory | Session |
| `db/crud.py` | DB read/write operations | Records |
| `api/pipeline.py` | Unified per-frame orchestration | Frame + alerts + metrics |

---

## Pipeline Metrics

Metrics displayed live on feed and dashboard:

| Metric | Calculation | Typical Value |
|---|---|---|
| **FPS** | `frame_count / elapsed_seconds` | 20–30 on GPU |
| **Detection Latency** | YOLO inference time per frame | 8–15ms |
| **Active Workers** | Tracked workers in current frame | Varies |
| **Critical Violations** | Running count of CRITICAL+HIGH logged | Session total |
| **Falls Detected** | Subset of fall violation count | Session total |

---

## Environment Variables

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Groq API key for LLaMA models |
| `DATABASE_URL` | PostgreSQL connection string |

---


## License

MIT License — free to use, modify, and distribute.

---

*Built with YOLOv8 · OpenCV · Groq LLaMA · Streamlit*
