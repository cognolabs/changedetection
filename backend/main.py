import sys
from pathlib import Path

# Ensure project root (parent of backend/) is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.database import init_db
from backend.config import FRAMES_DIR
from backend.routers import properties, videos, inference, changes, demo

app = FastAPI(
    title="Property Typology Change Detection",
    version="0.1.0",
    description="Detect property typology mismatches using street-level video and YOLO inference",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve extracted frames as static files
app.mount("/static/frames", StaticFiles(directory=str(FRAMES_DIR)), name="frames")

app.include_router(properties.router, prefix="/api/properties", tags=["Properties"])
app.include_router(videos.router, prefix="/api/videos", tags=["Videos"])
app.include_router(inference.router, prefix="/api/inference", tags=["Inference"])
app.include_router(changes.router, prefix="/api/changes", tags=["Changes"])
app.include_router(demo.router, prefix="/api/demo", tags=["Demo"])


@app.on_event("startup")
def on_startup():
    init_db()


@app.get("/api/health")
def health_check():
    return {"status": "ok"}
