import os
import uuid
import hashlib
import sys
import traceback
import logging
import requests
import time
from flask import Flask, render_template, request, jsonify, url_for, send_from_directory
from ultralytics import YOLO
import cv2
import webbrowser
from threading import Timer
import database as db

# -----------------------
# Setup Logging (UTF-8 for Windows)
# -----------------------
log_file = "yolo_app_debug.log"
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Set UTF-8 for console on Windows
if sys.platform.startswith('win'):
    sys.stdout.reconfigure(encoding='utf-8')

logger.info("=" * 80)
logger.info("APPLICATION STARTING")
logger.info("=" * 80)

# -----------------------
# Config
# -----------------------
if getattr(sys, 'frozen', False):
    app_data_path = os.path.join(os.getenv('APPDATA'), 'YOLODetector')
    UPLOAD_FOLDER = os.path.join(app_data_path, 'uploads')
    RESULT_FOLDER = os.path.join(app_data_path, 'results')
    MODEL_PATH = os.path.join(sys._MEIPASS, 'best.pt')
else:
    UPLOAD_FOLDER = os.path.join(os.getcwd(), "static", "uploads")
    RESULT_FOLDER = os.path.join(os.getcwd(), "static", "results")
    MODEL_PATH = os.path.join(os.getcwd(), "best.pt")

logger.info(f"Working Directory: {os.getcwd()}")
logger.info(f"UPLOAD_FOLDER: {UPLOAD_FOLDER}")
logger.info(f"RESULT_FOLDER: {RESULT_FOLDER}")
logger.info(f"MODEL_PATH: {MODEL_PATH}")

# Create directories
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(RESULT_FOLDER, exist_ok=True)
    logger.info("[OK] Folders created successfully")
except Exception as e:
    logger.error(f"[ERROR] Failed to create folders: {e}")

# Check model file
if os.path.exists(MODEL_PATH):
    logger.info("[OK] Model file found")
    logger.info(f"  File size: {os.path.getsize(MODEL_PATH) / (1024*1024):.2f} MB")
else:
    logger.error(f"[ERROR] MODEL FILE NOT FOUND at: {MODEL_PATH}")

# Flask app
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["RESULT_FOLDER"] = RESULT_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024  # 500MB max

# Load model
model = None
try:
    logger.info("Loading YOLO model...")
    model = YOLO(MODEL_PATH)
    logger.info("[OK] Model loaded successfully")
    logger.info(f"Model names: {model.names}")
except Exception as e:
    logger.error(f"[ERROR] Failed to load model: {e}")
    logger.error(traceback.format_exc())

IMG_SIZE = 1280
CONF_THRESH = 0.25
OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "llava:7b"  # Multimodal model for image analysis

def check_ollama_available():
    """Check if Ollama is running and accessible"""
    try:
        response = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
        return response.status_code == 200
    except Exception:
        return False

def get_semantic_explanation(detections: dict, image_path: str = None, detection_details: list = None) -> dict:
    """Get structured LLM explanation for detected classes
    
    Returns a structured analysis with:
    - threat_level: Low/Medium/High/Critical assessment
    - infrastructure_analysis: What the detected infrastructure reveals
    - strategic_assessment: Tactical and strategic significance
    - spatial_patterns: Relationship between detected objects
    - recommendations: Suggested follow-up actions
    
    For multimodal models like LLaVA, also pass the image.
    """
    import base64
    
    try:
        if not detections or sum(detections.values()) == 0:
            return None
        
        # Filter active detections
        active_detections = {name: count for name, count in detections.items() if count > 0}
        total_objects = sum(active_detections.values())
        
        # Build detection summary with confidence info if available
        detection_summary = []
        for name, count in active_detections.items():
            detection_summary.append(f"• {name}: {count} instance(s)")
        
        # Domain-specific context for cantonment/military areas
        infrastructure_context = """
DOMAIN KNOWLEDGE - Military/Cantonment Infrastructure:
- Aircraft/Helicopters: Indicate air operations capability, patrol frequency
- Hangars: Suggest maintenance facilities, fleet size capacity
- Bunkers/Shelters: Defensive posture, protection of assets
- Vehicles/Trucks: Logistics capability, troop movement potential
- Runways/Helipads: Operational tempo, deployment readiness
- Storage facilities: Supply chain, operational sustainability
- Radar/Communication: Surveillance capability, command structure
- Barracks/Buildings: Personnel capacity, permanent vs temporary deployment
"""
        
        # Enhanced structured prompt
        prompt = f"""You are a defense intelligence analyst examining satellite imagery of a military/cantonment facility with AI-detected objects highlighted.

{infrastructure_context}

DETECTED OBJECTS IN THIS IMAGE:
{chr(10).join(detection_summary)}
Total objects detected: {total_objects}

Analyze this facility and provide a STRUCTURED assessment in the following exact format:

**THREAT LEVEL:** [Choose: LOW | MEDIUM | HIGH | CRITICAL] - [One sentence justification]

**INFRASTRUCTURE ANALYSIS:**
[2-3 sentences about what the detected infrastructure reveals about this facility's purpose and capabilities]

**STRATEGIC ASSESSMENT:**
[2-3 sentences on tactical significance, operational readiness, and any patterns suggesting activity level]

**SPATIAL PATTERNS:**
[1-2 sentences on how the detected objects relate to each other spatially - clustering, dispersal, proximity patterns]

**KEY OBSERVATIONS:**
[2-3 bullet points of the most important intelligence insights]

Be specific about what the DETECTED objects reveal. Base your analysis solely on visible evidence."""
        
        logger.info(f"Requesting structured semantic analysis from Ollama ({OLLAMA_MODEL})...")
        
        # Build request payload
        payload = {
            'model': OLLAMA_MODEL,
            'prompt': prompt,
            'stream': False
        }
        
        # For multimodal models like LLaVA, include the image
        if image_path and OLLAMA_MODEL.lower().startswith('llava'):
            try:
                with open(image_path, 'rb') as img_file:
                    image_data = base64.b64encode(img_file.read()).decode('utf-8')
                payload['images'] = [image_data]
                logger.info(f"Including image for multimodal analysis")
            except Exception as img_err:
                logger.warning(f"Could not encode image: {img_err}")
        
        response = requests.post(f"{OLLAMA_URL}/api/generate", json=payload, timeout=120)
        
        if response.status_code == 200:
            raw_response = response.json().get('response', '')
            logger.info(f"Semantic analysis received: {len(raw_response)} chars")
            
            # Parse structured response into sections
            structured_analysis = parse_structured_analysis(raw_response, active_detections, total_objects)
            return structured_analysis
        else:
            logger.warning(f"Ollama returned status {response.status_code}: {response.text[:200]}")
            return None
    except Exception as e:
        logger.error(f"Error getting semantic explanation: {e}")
        return None


def parse_structured_analysis(raw_text: str, detections: dict, total_objects: int) -> dict:
    """Parse LLM response into structured sections"""
    import re
    
    result = {
        "raw_analysis": raw_text,
        "threat_level": "UNKNOWN",
        "threat_justification": "",
        "infrastructure_analysis": "",
        "strategic_assessment": "",
        "spatial_patterns": "",
        "key_observations": [],
        "detection_summary": {
            "total_objects": total_objects,
            "object_breakdown": detections
        }
    }
    
    try:
        # Extract threat level
        threat_match = re.search(r'\*\*THREAT LEVEL:\*\*\s*(LOW|MEDIUM|HIGH|CRITICAL)[:\s-]*(.+?)(?=\*\*|$)', raw_text, re.IGNORECASE | re.DOTALL)
        if threat_match:
            result["threat_level"] = threat_match.group(1).upper()
            result["threat_justification"] = threat_match.group(2).strip()[:200]
        
        # Extract infrastructure analysis
        infra_match = re.search(r'\*\*INFRASTRUCTURE ANALYSIS:\*\*\s*(.+?)(?=\*\*|$)', raw_text, re.IGNORECASE | re.DOTALL)
        if infra_match:
            result["infrastructure_analysis"] = infra_match.group(1).strip()[:500]
        
        # Extract strategic assessment
        strategic_match = re.search(r'\*\*STRATEGIC ASSESSMENT:\*\*\s*(.+?)(?=\*\*|$)', raw_text, re.IGNORECASE | re.DOTALL)
        if strategic_match:
            result["strategic_assessment"] = strategic_match.group(1).strip()[:500]
        
        # Extract spatial patterns
        spatial_match = re.search(r'\*\*SPATIAL PATTERNS:\*\*\s*(.+?)(?=\*\*|$)', raw_text, re.IGNORECASE | re.DOTALL)
        if spatial_match:
            result["spatial_patterns"] = spatial_match.group(1).strip()[:300]
        
        # Extract key observations (bullet points)
        obs_match = re.search(r'\*\*KEY OBSERVATIONS:\*\*\s*(.+?)(?=\*\*|$)', raw_text, re.IGNORECASE | re.DOTALL)
        if obs_match:
            obs_text = obs_match.group(1).strip()
            # Parse bullet points
            bullets = re.findall(r'[-•*]\s*(.+?)(?=[-•*]|$)', obs_text, re.DOTALL)
            result["key_observations"] = [b.strip()[:200] for b in bullets if b.strip()][:5]
        
        logger.info(f"Parsed analysis - Threat: {result['threat_level']}, Observations: {len(result['key_observations'])}")
        
    except Exception as e:
        logger.error(f"Error parsing structured analysis: {e}")
        # Fallback - return raw analysis
        result["infrastructure_analysis"] = raw_text[:500] if raw_text else "Analysis unavailable"
    
    return result

def name_to_hex(name: str) -> str:
    """Generate deterministic hex color from name"""
    try:
        h = hashlib.md5(name.encode()).hexdigest()
        r = int(h[0:2], 16)
        g = int(h[2:4], 16)
        b = int(h[4:6], 16)
        def bump(x): return int(80 + (x / 255.0) * 175)
        r, g, b = bump(r), bump(g), bump(b)
        return '#{:02x}{:02x}{:02x}'.format(r, g, b)
    except Exception as e:
        logger.error(f"Error in name_to_hex: {e}")
        return "#cccccc"

# Log all incoming requests for debugging
@app.before_request
def log_requests():
    logger.info(f"[REQUEST] {request.method} {request.path} | User-Agent: {request.headers.get('User-Agent', 'Unknown')}")
    if request.files:
        logger.info(f"[FILES] Received: {list(request.files.keys())}")
    if request.path == '/api/process':
        logger.info(f"[API] Process request headers: {dict(request.headers)}")

@app.route("/")
def index():
    selected = request.args.get("sat", "")
    logger.debug(f"[ROUTE] Index accessed with sat={selected}")
    return render_template("index.html", selected_sat=selected)

@app.route("/satellite/<sat>")
def satellite(sat):
    logger.debug(f"[ROUTE] Satellite accessed: {sat}")
    return render_template("index.html", selected_sat=sat)

@app.route("/api/status")
def api_status():
    """Check system status including Ollama availability"""
    ollama_available = check_ollama_available()
    logger.info(f"[STATUS] Ollama available: {ollama_available}")
    return jsonify({
        "model_loaded": model is not None,
        "ollama_available": ollama_available,
        "ollama_model": OLLAMA_MODEL if ollama_available else None
    })

@app.route("/debug")
def debug():
    """Debug endpoint to check system status"""
    logger.info("[ROUTE] Debug endpoint accessed")
    try:
        debug_info = {
            "status": "ok",
            "model_loaded": model is not None,
            "model_path": MODEL_PATH,
            "model_path_exists": os.path.exists(MODEL_PATH),
            "upload_folder": UPLOAD_FOLDER,
            "upload_folder_exists": os.path.exists(UPLOAD_FOLDER),
            "result_folder": RESULT_FOLDER,
            "result_folder_exists": os.path.exists(RESULT_FOLDER),
            "ollama_available": check_ollama_available(),
            "ollama_model": OLLAMA_MODEL
        }
        
        if model:
            debug_info["model_names"] = dict(model.names) if model.names else {}
        
        logger.info(f"[DEBUG] Info: {debug_info}")
        return jsonify(debug_info)
    except Exception as e:
        logger.error(f"[ERROR] Debug endpoint: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route("/api/process", methods=["POST"])
def process():
    logger.info("=" * 80)
    logger.info("[API] /process endpoint called - Starting detection")
    logger.info("=" * 80)
    
    try:
        if model is None:
            error_msg = "Model not loaded"
            logger.error(f"[ERROR] {error_msg}")
            return jsonify({"error": error_msg}), 500
        
        logger.info(f"[REQUEST] Files: {list(request.files.keys())}")
        if "images[]" not in request.files:
            logger.error("[ERROR] No 'images[]' in request.files")
            return jsonify({"error": "No file uploaded"}), 400

        file = request.files["images[]"]
        
        if file.filename == "":
            logger.error("[ERROR] Empty filename")
            return jsonify({"error": "No selected file"}), 400

        logger.info(f"[OK] File received: {file.filename}")

        # Save file
        filename = f"{uuid.uuid4().hex}_{file.filename}"
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        
        try:
            logger.info(f"Saving file to: {filepath}")
            file.save(filepath)
            logger.info(f"[OK] File saved: {os.path.exists(filepath)}")
        except Exception as e:
            logger.error(f"[ERROR] Failed to save file: {e}")
            return jsonify({"error": f"Failed to save file: {str(e)}"}), 500

        # Read and process image (rest same as before - abbreviated for space)
        try:
            start_time = time.time()  # Start timing for DB logging
            
            img = cv2.imread(filepath)
            if img is None:
                logger.error(f"[ERROR] OpenCV failed to read image")
                return jsonify({"error": "Failed to read image"}), 400
            
            logger.info(f"[OK] Image read, shape: {img.shape}")

            # Use direct model call instead of .predict() to avoid ultralytics bug
            results = model(
                filepath, 
                imgsz=IMG_SIZE, 
                conf=CONF_THRESH, 
                device="cpu",  # GPU requires PyTorch with CUDA
                verbose=False
            )
            
            logger.info(f"[OK] Inference done, results: {len(results)}")

            if not results or len(results) == 0:
                return jsonify({"error": "No detection results"}), 500

            result = results[0]
            names_map = model.names if hasattr(model, 'names') and model.names else {}
            class_counts = {name: 0 for name in names_map.values()}
            
            confs = []
            cls_ids = []
            xyxy = []
            
            if result.boxes is not None and len(result.boxes) > 0:
                confs = result.boxes.conf.cpu().numpy()
                cls_ids = result.boxes.cls.cpu().numpy().astype(int)
                xyxy = result.boxes.xyxy.cpu().numpy()
                logger.info(f"[OK] Extracted {len(confs)} detections")
            else:
                logger.info("No boxes detected")

            # Count detections
            for conf, cid in zip(confs, cls_ids):
                if float(conf) >= CONF_THRESH:
                    cname = names_map.get(int(cid), f"class_{int(cid)}")
                    class_counts[cname] = class_counts.get(cname, 0) + 1

            total_detections = sum(class_counts.values())
            
            class_colors = {name: name_to_hex(name) for name in names_map.values()}

            # Draw boxes with labels (generate both versions)
            orig = cv2.imread(filepath)
            orig_no_labels = orig.copy()  # Keep a copy for the no-labels version
            
            # Collect object details for database
            detection_objects = []
            
            if len(confs) > 0:
                h, w = orig.shape[:2]
                thickness = max(2, int(round(min(h, w) / 300.0)))
                font_scale = max(0.5, min(h, w) / 800.0)
                font_thickness = max(1, int(font_scale * 2))
                
                for conf, cid, box in zip(confs, cls_ids, xyxy):
                    if float(conf) < CONF_THRESH:
                        continue
                    cname = names_map.get(int(cid), f"class_{int(cid)}")
                    hexcol = class_colors.get(cname, "#cccccc")
                    r, g, b = int(hexcol[1:3], 16), int(hexcol[3:5], 16), int(hexcol[5:7], 16)
                    color = (b, g, r)
                    x1, y1, x2, y2 = map(int, box)
                    
                    # Draw bounding box on BOTH images
                    cv2.rectangle(orig, (x1, y1), (x2, y2), (0, 0, 0), thickness=thickness+2, lineType=cv2.LINE_AA)
                    cv2.rectangle(orig, (x1, y1), (x2, y2), color, thickness=thickness, lineType=cv2.LINE_AA)
                    cv2.rectangle(orig_no_labels, (x1, y1), (x2, y2), (0, 0, 0), thickness=thickness+2, lineType=cv2.LINE_AA)
                    cv2.rectangle(orig_no_labels, (x1, y1), (x2, y2), color, thickness=thickness, lineType=cv2.LINE_AA)
                    
                    # Draw label ONLY on the labeled version
                    label = f"{cname} {float(conf):.2f}"
                    (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, font_scale, font_thickness)
                    label_y1 = max(y1 - th - 10, 0)
                    label_y2 = y1
                    cv2.rectangle(orig, (x1, label_y1), (x1 + tw + 6, label_y2), color, -1)
                    cv2.putText(orig, label, (x1 + 3, label_y2 - 4), cv2.FONT_HERSHEY_SIMPLEX, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
                    
                    # Collect object details for database
                    detection_objects.append({
                        'class_name': cname,
                        'confidence': float(conf),
                        'bbox_x1': x1, 'bbox_y1': y1,
                        'bbox_x2': x2, 'bbox_y2': y2
                    })

            # Save BOTH versions
            result_filename = f"result_{filename}"
            result_filename_no_labels = f"result_nolabel_{filename}"
            result_path = os.path.join(app.config["RESULT_FOLDER"], result_filename)
            result_path_no_labels = os.path.join(app.config["RESULT_FOLDER"], result_filename_no_labels)
            cv2.imwrite(result_path, orig)
            cv2.imwrite(result_path_no_labels, orig_no_labels)
            
            processed_url = url_for("static", filename=f"results/{result_filename}", _external=False)
            processed_url_no_labels = url_for("static", filename=f"results/{result_filename_no_labels}", _external=False)

            # Check Ollama and get semantic explanation if available
            ollama_available = check_ollama_available()
            semantic_explanation = None
            
            if ollama_available and total_detections > 0:
                semantic_explanation = get_semantic_explanation(class_counts, result_path)
            
            response = {
                "processedImages": [{"url": processed_url, "downloadUrl": processed_url, "urlNoLabels": processed_url_no_labels}],
                "detections": class_counts,
                "classColors": class_colors,
                "total": total_detections,
                "ollama_available": ollama_available,
                "semantic_explanation": semantic_explanation
            }
            
            # Log to database
            processing_time_ms = (time.time() - start_time) * 1000
            threat_level = semantic_explanation.get('threat_level') if semantic_explanation else None
            h, w = orig.shape[:2]
            
            try:
                detection_id = db.log_detection(
                    image_name=filename,
                    image_width=w,
                    image_height=h,
                    total_objects=total_detections,
                    processing_time_ms=processing_time_ms,
                    result_image_path=f"results/{result_filename}",
                    result_image_nolabel_path=f"results/{result_filename_no_labels}",
                    threat_level=threat_level,
                    llm_analysis=semantic_explanation,
                    objects=detection_objects
                )
                logger.info(f"[DB] Detection logged with ID: {detection_id}")
            except Exception as db_error:
                logger.warning(f"[DB] Failed to log detection: {db_error}")
            
            logger.info(f"[OK] Response ready: total={total_detections}, ollama={ollama_available}")
            return jsonify(response), 200
            
        except Exception as e:
            logger.error(f"[ERROR] Processing: {e}")
            return jsonify({"error": f"Processing failed: {str(e)}"}), 500
            
    except Exception as e:
        logger.error(f"[CRITICAL] Error: {e}")
        return jsonify({"error": f"Critical error: {str(e)}"}), 500

# Static serving
@app.route("/static/uploads/<filename>")
def serve_upload(filename):
    logger.debug(f"[SERVE] Upload: {filename}")
    return send_from_directory(UPLOAD_FOLDER, filename)

@app.route("/static/results/<filename>")
def serve_result(filename):
    logger.debug(f"[SERVE] Result: {filename}")
    return send_from_directory(RESULT_FOLDER, filename)

# History API endpoints
@app.route("/history")
def history_page():
    """Serve the detection history page with initial data for instant loading"""
    try:
        stats = db.get_stats()
        history = db.get_history(limit=50)
        return render_template("history.html", stats=stats, history=history)
    except Exception as e:
        logger.error(f"Failed to load history page data: {e}")
        return render_template("history.html", stats={}, history=[])

@app.route("/api/history")
def api_history():
    """Get detection history with pagination"""
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    history = db.get_history(limit=limit, offset=offset)
    return jsonify({"history": history})

@app.route("/api/history/<int:detection_id>")
def api_detection_details(detection_id):
    """Get full details for a specific detection"""
    details = db.get_detection_details(detection_id)
    if not details:
        return jsonify({"error": "Detection not found"}), 404
    return jsonify(details)

@app.route("/api/stats")
def api_stats():
    """Get overall detection statistics"""
    stats = db.get_stats()
    return jsonify(stats)

@app.route("/api/history/<int:detection_id>", methods=["DELETE"])
def api_delete_detection(detection_id):
    """Delete a detection record"""
    deleted = db.delete_detection(detection_id)
    if deleted:
        return jsonify({"success": True})
    return jsonify({"error": "Detection not found"}), 404


def open_browser():
    webbrowser.open('http://127.0.0.1:5000/')

if __name__ == "__main__":
    logger.info("Starting Flask server...")
    
    if getattr(sys, 'frozen', False):
        timer = Timer(2, open_browser)
        timer.daemon = True
        timer.start()
    
    logger.info("Server running on http://127.0.0.1:5000")
    logger.info("Debug endpoint: http://127.0.0.1:5000/debug")
    logger.info(f"Log file: {log_file}")
    
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
