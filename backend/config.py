from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
FRAMES_DIR = DATA_DIR / "frames"
MODELS_DIR = DATA_DIR / "models"
DB_DIR = DATA_DIR / "db"

DATABASE_URL = f"sqlite:///{DB_DIR / 'changedetection.db'}"

# Ensure directories exist
for d in [UPLOAD_DIR, FRAMES_DIR, MODELS_DIR, DB_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Video processing
FRAME_INTERVAL_SEC = 1.0  # Extract 1 frame per second

# Geo-matching
BUFFER_METERS = 30  # Buffer distance for matching frames to properties

# Change detection
CONFIDENCE_THRESHOLD = 0.5  # Minimum confidence to flag a mismatch
MIN_FRAMES_FOR_PREDICTION = 1  # Minimum frames needed for reliable prediction
