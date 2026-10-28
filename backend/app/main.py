import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.database import init_db
from app.routes.suggestion_routes import router as suggestion_router
from app.routes.project_routes import router as project_router
from app.routes.script_routes import router as script_router
from app.routes.voice_routes import router as voice_router
from app.routes.trailer_routes import router as trailer_router
from app.routes.scene_routes import router as scene_router
from app.routes.thumbnail_routes import router as thumbnail_router
from app.routes.video_routes import router as video_router
from app.routes.bgm_routes import router as bgm_router
from app.routes.youtube_upload_routes import router as youtube_upload_router
from app.routes.youtube_oauth_routes import router as youtube_oauth_router
from app.routes.cinematic_routes import router as cinematic_router
from app.routes.processing_queue_routes import router as queue_router
from app.services.processing_queue_service import processing_queue

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger(__name__)

# Initialize DB
init_db()

app = FastAPI(
    title=settings.app_name,
    description="Backend API for AI Movie Suggestion and Group Shorts Video Studio",
    version="1.0.0",
)

# CORS Middleware - allows access from web browsers, mobile phones, and Vercel
cors_origins_env = settings.storage_path.parent  # reference
raw_origins = os.getenv("CORS_ORIGINS", "*").strip()
allow_origins = [o.strip() for o in raw_origins.split(",") if o.strip()] if raw_origins != "*" else ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Routes
app.include_router(suggestion_router, prefix="/api")
app.include_router(project_router, prefix="/api")
app.include_router(script_router, prefix="/api")
app.include_router(voice_router, prefix="/api")
app.include_router(trailer_router, prefix="/api")
app.include_router(scene_router, prefix="/api")
app.include_router(thumbnail_router, prefix="/api")
app.include_router(video_router, prefix="/api")
app.include_router(bgm_router, prefix="/api")
app.include_router(youtube_upload_router, prefix="/api")
app.include_router(youtube_oauth_router, prefix="/api")
app.include_router(cinematic_router, prefix="/api")
app.include_router(queue_router, prefix="/api")


@app.on_event('startup')
def start_processing_queue():
    processing_queue.start_worker()
    from app.services.publishing_automation_service import publishing_automation
    publishing_automation.start_worker()


from app.routes.publishing_automation_routes import router as publishing_automation_router
app.include_router(publishing_automation_router, prefix='/api')

# Static files for local media access
app.mount("/storage", StaticFiles(directory=str(settings.storage_path)), name="storage")


@app.get("/")
def root():
    return {
        "status": "online",
        "app": settings.app_name,
        "docs": "/docs",
        "endpoints": [
            "/api/suggestions/categories",
            "/api/suggestions/suggest",
            "/api/suggestions/search",
            "/api/projects",
        ],
    }


@app.get("/api/health")
def health():
    return {"status": "healthy", "database": "connected"}
