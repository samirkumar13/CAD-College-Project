# PyInstaller Build Errors Reference

Common errors encountered when building the CAD System EXE with PyInstaller and Inno Setup, along with their fixes.

---

## 1. `sqlite3.OperationalError: unable to open database file`

**Cause**: PyInstaller bundles files into a read-only temp directory (`_MEIPASS`). `database.py` was using `os.path.dirname(__file__)` to locate `detections.db`, which points to `_MEIPASS` — a read-only location.

**Fix** (in `database.py`):
```python
if getattr(sys, 'frozen', False):
    _db_dir = os.path.join(os.getenv('APPDATA'), 'YOLODetector')
    os.makedirs(_db_dir, exist_ok=True)
    DB_PATH = os.path.join(_db_dir, "detections.db")
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), "detections.db")
```

---

## 2. `PermissionError: [Errno 13] Permission denied: '...\yolo_app_debug.log'`

**Cause**: The log file path was relative (`yolo_app_debug.log`). When installed to `C:\Program Files (x86)\`, writing there requires admin privileges.

**Fix** (in `app.py`):
```python
if getattr(sys, 'frozen', False):
    _log_dir = os.path.join(os.getenv('APPDATA'), 'YOLODetector')
    os.makedirs(_log_dir, exist_ok=True)
    log_file = os.path.join(_log_dir, "yolo_app_debug.log")
else:
    log_file = "yolo_app_debug.log"
```

---

## 3. `AttributeError: 'NoneType' object has no attribute 'reconfigure'`

**Cause**: PyInstaller `--noconsole` mode sets `sys.stdout = None` since there's no console window. Two places used `sys.stdout`:
- `logging.StreamHandler(sys.stdout)` — crashes during logger setup
- `sys.stdout.reconfigure(encoding='utf-8')` — crashes on reconfigure

**Fix** (in `app.py`):
```python
# Guard StreamHandler
_log_handlers = [logging.FileHandler(log_file, encoding='utf-8')]
if sys.stdout is not None:
    _log_handlers.append(logging.StreamHandler(sys.stdout))

# Guard reconfigure
if sys.platform.startswith('win') and sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8')
```

---

## 4. App crashes / doesn't start without Ollama (ERR_CONNECTION_REFUSED)

**Cause**: A blocking `tkinter.messagebox` popup ran on the main thread **before** `app.run()`, preventing Flask from starting. Additionally, `tkinter` can fail in `--noconsole` mode.

**Fix** (in `app.py`): Use `ctypes.windll.user32.MessageBoxW` (native Windows API) in a **background thread**:
```python
def show_ollama_warning():
    """Runs in a daemon thread — never blocks Flask."""
    if not check_ollama_available():
        ctypes.windll.user32.MessageBoxW(0, "message", "title", 0x40)

# In __main__:
ollama_thread = Thread(target=show_ollama_warning, daemon=True)
ollama_thread.start()
# Flask starts immediately after, regardless of popup
app.run(...)
```

---

## 5. `pyinstaller` command not recognized (even with venv activated)

**Cause**: The venv `.exe` launchers (`pip.exe`, `pyinstaller.exe`) have hardcoded Python paths baked in. If the project folder was moved/renamed, these paths break.

**Fix**: Use `python -m` prefix:
```powershell
python -m PyInstaller app.spec --noconfirm
python -m pip install <package>
```

**Permanent fix**: Recreate the venv:
```powershell
python -m venv venv --clear
python -m pip install -r requirements.txt
```

---

## 6. Uninstaller doesn't remove files

**Cause**: The Flask server runs in the background, locking files. Inno Setup can't delete locked files.

**Fix** (in `setup.iss`):
```ini
[Setup]
CloseApplications=force

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM CAD_System.exe"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
Type: filesandordirs; Name: "{userappdata}\YOLODetector"
```

---

## General Rule

> **Any file that needs to be WRITTEN at runtime (database, logs, uploads, results) must use `%APPDATA%\YOLODetector\` when running as a frozen EXE, because `Program Files` is read-only.**

## Build Commands Quick Reference

```powershell
# Clean cache
Remove-Item -Recurse -Force build, dist, __pycache__ -ErrorAction SilentlyContinue

# Build EXE
python -m PyInstaller app.spec --noconfirm

# Build installer
& "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" setup.iss
```
