"""
SQLite Database Module for Cantonment Area Detection System
Stores detection history, confidence scores, processing metrics, and LLM analysis.
"""

import sqlite3
import os
import sys
import json
from datetime import datetime
from typing import Optional, List, Dict, Any

# Database path — use APPDATA when running as a frozen PyInstaller exe
# (PyInstaller's _MEIPASS temp directory is read-only)
if getattr(sys, 'frozen', False):
    _db_dir = os.path.join(os.getenv('APPDATA'), 'YOLODetector')
    os.makedirs(_db_dir, exist_ok=True)
    DB_PATH = os.path.join(_db_dir, "detections.db")
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "detections.db")


def get_connection():
    """Get database connection with row factory for dict-like access."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialize database tables if they don't exist."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Main detections table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            image_name TEXT NOT NULL,
            image_width INTEGER,
            image_height INTEGER,
            total_objects INTEGER DEFAULT 0,
            processing_time_ms REAL,
            threat_level TEXT,
            result_image_path TEXT,
            result_image_nolabel_path TEXT,
            llm_analysis TEXT
        )
    """)
    
    # Detection objects table (per-object details)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS detection_objects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            detection_id INTEGER NOT NULL,
            class_name TEXT NOT NULL,
            confidence REAL,
            bbox_x1 INTEGER,
            bbox_y1 INTEGER,
            bbox_x2 INTEGER,
            bbox_y2 INTEGER,
            FOREIGN KEY (detection_id) REFERENCES detections(id) ON DELETE CASCADE
        )
    """)
    
    conn.commit()
    conn.close()


def log_detection(
    image_name: str,
    image_width: int,
    image_height: int,
    total_objects: int,
    processing_time_ms: float,
    result_image_path: str,
    result_image_nolabel_path: str,
    threat_level: Optional[str] = None,
    llm_analysis: Optional[dict] = None,
    objects: Optional[List[Dict]] = None
) -> int:
    """
    Log a detection result to the database.
    
    Returns: detection_id
    """
    conn = get_connection()
    cursor = conn.cursor()
    
    # Insert main detection record
    cursor.execute("""
        INSERT INTO detections 
        (image_name, image_width, image_height, total_objects, processing_time_ms,
         result_image_path, result_image_nolabel_path, threat_level, llm_analysis)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        image_name,
        image_width,
        image_height,
        total_objects,
        processing_time_ms,
        result_image_path,
        result_image_nolabel_path,
        threat_level,
        json.dumps(llm_analysis) if llm_analysis else None
    ))
    
    detection_id = cursor.lastrowid
    
    # Insert per-object details
    if objects:
        for obj in objects:
            cursor.execute("""
                INSERT INTO detection_objects 
                (detection_id, class_name, confidence, bbox_x1, bbox_y1, bbox_x2, bbox_y2)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                detection_id,
                obj.get('class_name'),
                obj.get('confidence'),
                obj.get('bbox_x1'),
                obj.get('bbox_y1'),
                obj.get('bbox_x2'),
                obj.get('bbox_y2')
            ))
    
    conn.commit()
    conn.close()
    
    return detection_id


def get_history(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Get detection history with pagination."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, timestamp, image_name, image_width, image_height,
               total_objects, processing_time_ms, threat_level,
               result_image_path, result_image_nolabel_path
        FROM detections
        ORDER BY timestamp DESC
        LIMIT ? OFFSET ?
    """, (limit, offset))
    
    rows = cursor.fetchall()
    conn.close()
    
    return [dict(row) for row in rows]


def get_detection_details(detection_id: int) -> Optional[Dict[str, Any]]:
    """Get full details for a specific detection including all objects."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Get main detection
    cursor.execute("""
        SELECT * FROM detections WHERE id = ?
    """, (detection_id,))
    
    row = cursor.fetchone()
    if not row:
        conn.close()
        return None
    
    result = dict(row)
    
    # Parse LLM analysis JSON
    if result.get('llm_analysis'):
        try:
            result['llm_analysis'] = json.loads(result['llm_analysis'])
        except:
            pass
    
    # Get objects
    cursor.execute("""
        SELECT class_name, confidence, bbox_x1, bbox_y1, bbox_x2, bbox_y2
        FROM detection_objects WHERE detection_id = ?
    """, (detection_id,))
    
    result['objects'] = [dict(r) for r in cursor.fetchall()]
    
    conn.close()
    return result


def get_stats() -> Dict[str, Any]:
    """Get overall detection statistics."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Total detections
    cursor.execute("SELECT COUNT(*) as count FROM detections")
    total = cursor.fetchone()['count']
    
    # Total objects detected
    cursor.execute("SELECT SUM(total_objects) as count FROM detections")
    total_objects = cursor.fetchone()['count'] or 0
    
    # Average processing time
    cursor.execute("SELECT AVG(processing_time_ms) as avg FROM detections")
    avg_time = cursor.fetchone()['avg'] or 0
    
    # Threat level breakdown
    cursor.execute("""
        SELECT threat_level, COUNT(*) as count 
        FROM detections 
        WHERE threat_level IS NOT NULL
        GROUP BY threat_level
    """)
    threat_levels = {row['threat_level']: row['count'] for row in cursor.fetchall()}
    
    # Most common objects
    cursor.execute("""
        SELECT class_name, COUNT(*) as count 
        FROM detection_objects 
        GROUP BY class_name 
        ORDER BY count DESC
        LIMIT 10
    """)
    common_objects = {row['class_name']: row['count'] for row in cursor.fetchall()}
    
    conn.close()
    
    return {
        'total_detections': total,
        'total_objects_detected': total_objects,
        'avg_processing_time_ms': round(avg_time, 2),
        'threat_level_breakdown': threat_levels,
        'most_common_objects': common_objects
    }


def delete_detection(detection_id: int) -> bool:
    """Delete a detection and its objects."""
    conn = get_connection()
    cursor = conn.cursor()
    
    cursor.execute("DELETE FROM detection_objects WHERE detection_id = ?", (detection_id,))
    cursor.execute("DELETE FROM detections WHERE id = ?", (detection_id,))
    
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    
    return deleted


# Initialize DB on module import
init_db()
