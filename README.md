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
├── app.py                 # Main Flask application
├── database.py            # SQLite database interactions
├── testmodel.py           # Model testing script
├── best.pt                # Trained YOLOv8 model weights
├── requirements.txt       # Python dependencies
├── .gitignore             # Git ignore rules
├── ARCHITECTURE.md        # Architecture overview
├── static/
│   ├── css/style.css     # Tactical dark theme styles
│   ├── js/main.js        # Frontend JavaScript
│   ├── icon.ico          # Application favicon/logo
│   ├── uploads/          # Directory for uploaded images
│   └── results/          # Directory for processed overlays
├── templates/
│   └── index.html        # Main HTML template
└── training_logs/        # Model training artifacts
    ├── args.yaml         # Training configuration
    ├── results.csv       # Training metrics
    ├── results.png       # Training curves visualization
    ├── confusion_matrix.png
    ├── *_curve.png       # F1, PR, P, R curves
    ├── train_batch*.jpg  # Training sample images
    ├── val_batch*.jpg    # Validation sample images
    └── weights/
        ├── best.pt       # Best model weights
        └── last.pt       # Final epoch weights
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
