# System Architecture - Cantonment Area Detection System

## High-Level Architecture

```mermaid
flowchart TB
    subgraph Client["Frontend (Browser)"]
        UI[/"Web Interface<br/>HTML/CSS/JS"/]
    end

    subgraph Server["Flask Backend (Python)"]
        API["REST API<br/>/api/process<br/>/api/status<br/>/api/history"]
        PROC["Image Processing<br/>OpenCV"]
        YOLO["Object Detection<br/>YOLOv8-L Segmentation"]
        LLM["Semantic Analysis<br/>Ollama LLaVA 7B"]
    end

    subgraph Storage["Data Layer"]
        DB[("SQLite Database<br/>detections<br/>detection_objects")]
        FS[/"File System<br/>uploads/<br/>results/"/]
        MODEL[/"Model Weights<br/>best.pt (92MB)"/]
    end

    UI -->|"Upload Image"| API
    API --> PROC
    PROC --> YOLO
    YOLO -->|"Detection Results"| LLM
    LLM -->|"Threat Analysis"| API
    API -->|"JSON Response"| UI
    
    YOLO -.->|"Load"| MODEL
    PROC -->|"Save"| FS
    API -->|"Log Results"| DB
```

## Data Flow

```mermaid
sequenceDiagram
    participant U as User
    participant F as Frontend
    participant A as Flask API
    participant Y as YOLOv8
    participant L as LLaVA LLM
    participant D as SQLite DB

    U->>F: Upload satellite image
    F->>A: POST /api/process
    A->>A: Save to uploads/
    A->>Y: Run inference
    Y-->>A: Bounding boxes + confidence
    A->>A: Draw detections on image
    A->>L: Send image + detections
    L-->>A: Threat analysis (JSON)
    A->>D: Log detection record
    A->>D: Log object details
    A-->>F: Response (image URL + analysis)
    F-->>U: Display results
```

## Component Details

| Component | Technology | Purpose |
|-----------|------------|---------|
| **Frontend** | HTML5, CSS3, JavaScript | User interface for image upload and result display |
| **Backend** | Flask (Python 3.9+) | REST API, request handling, orchestration |
| **Object Detection** | Ultralytics YOLOv8-L | Detect military objects in satellite imagery |
| **Semantic Analysis** | Ollama + LLaVA 7B | AI-powered threat assessment and interpretation |
| **Database** | SQLite | Store detection logs, metrics, and analysis |
| **Image Processing** | OpenCV | Image I/O, bounding box rendering |

## Database Schema

```mermaid
erDiagram
    DETECTIONS {
        int id PK
        datetime timestamp
        string image_name
        string image_size
        int total_objects
        float processing_time_ms
        string threat_level
        text llm_analysis
    }
    
    DETECTION_OBJECTS {
        int id PK
        int detection_id FK
        string class_name
        float confidence
        int bbox_x1
        int bbox_y1
        int bbox_x2
        int bbox_y2
    }
    
    DETECTIONS ||--o{ DETECTION_OBJECTS : contains
```
