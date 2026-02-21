# Cantonment Area Detection System

A Flask-based web application for detecting military/cantonment infrastructure in satellite imagery using YOLOv8 object detection with optional LLM-powered semantic analysis.

## Features

- **Object Detection**: YOLOv8-based detection of cantonment area objects (helicopters, vehicles, buildings, etc.)
- **Semantic Analysis**: AI-powered interpretation using Ollama LLM (optional)
- **Modern UI**: Tactical dark theme with real-time detection display
- **Label Toggle**: Switch between labeled/unlabeled detection results
- **Export**: Download processed images with detections

## Quick Start

### Prerequisites
- Python 3.9 or higher
- Git

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/samirkumar13/cant_backup.git
cd cant_backup

# 2. Create virtual environment
python -m venv venv

# 3. Activate virtual environment
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run the application
python app.py
```

The app will open automatically in your browser at `http://127.0.0.1:5000`

### Optional: Enable AI Semantic Analysis

To enable the AI-powered analysis feature:

1. Install Ollama from https://ollama.ai
2. Pull the LLaVA model:
   ```bash
   ollama pull llava:7b
   ```
3. Keep Ollama running in the background
4. Restart the Flask app - the AI module will show "ONLINE"

## Project Structure

```
cant_backup/
├── .git/                  # Git repository data
├── __pycache__/           # Compiled Python files
├── static/                # Static web assets
│   ├── css/               # Stylesheets (style.css)
│   ├── js/                # Client-side scripts (main.js)
│   ├── results/           # Processed image output
│   ├── uploads/           # User uploaded images
│   └── icon.ico           # Web favicon
├── templates/             # HTML templates
│   └── index.html         # Main dashboard interface
├── training_logs/         # Custom model training history & metrics
│   ├── weights/           # Trained model checkpoints
│   │   ├── best.pt        # Optimal weights
│   │   └── last.pt        # Final weights
│   ├── args.yaml          # Hyperparameters
│   ├── results.csv        # Epoch metrics
│   ├── results.png        # Training graphs
│   ├── confusion_matrix.png
│   ├── *_curve.png        # PR/F1 curve plots
│   ├── train_batch*.jpg   # Training examples
│   └── val_batch*.jpg     # Validation examples
├── venv/                  # Python virtual environment
├── .gitignore             # Git excluded files
├── app.py                 # Flask web server & inference logic
├── ARCHITECTURE.md        # System architecture documentation
├── best.pt                # Primary trained YOLOv8 model
├── database.py            # SQLite database manager
├── detections.db          # SQLite database (stores history)
├── README.md              # Project documentation
├── requirements.txt       # Python package dependencies
├── testmodel.py           # Quick CLI testing script
└── yolo_app_debug.log     # Application debug logs
```

## Usage

1. Click **"UPLOAD IMAGERY"** to select a satellite image
2. Click **"INITIATE ANALYSIS"** to run detection
3. View detected objects in the right panel
4. Toggle labels on/off using the switch in the viewport footer
5. Download the processed image using the **"DOWNLOAD"** button

## Model Information

- **Architecture**: YOLOv8 Large (Segmentation)
- **Classes**: Military/cantonment infrastructure objects
- **Training**: Custom dataset with augmentation
- **Inference**: CPU-based (GPU optional with CUDA)

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port 5000 in use | Change port in `app.py` or kill existing process |
| Model not loading | Ensure `best.pt` is in root directory |
| AI Analysis offline | Install and run Ollama with llava:7b model |
| Permission errors | Run terminal as administrator |

## License

For academic/personal use only.

---
*Last updated: January 2026*
