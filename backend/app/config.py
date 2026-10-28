import os
from pathlib import Path
from dotenv import load_dotenv

BACKEND_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = BACKEND_ROOT / ".env"

load_dotenv(dotenv_path=ENV_PATH)


class Settings:
    def __init__(self):
        # App
        self.app_name = os.getenv("APP_NAME", "Movie Suggestion & Group Shorts Automation").strip()
        self.app_env = os.getenv("APP_ENV", "development").strip()
        self.debug = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")
        self.host = os.getenv("HOST", "0.0.0.0").strip()
        self.port = int(os.getenv("PORT", "8000"))

        # TMDB API
        self.tmdb_bearer_token = os.getenv("TMDB_BEARER_TOKEN", "").strip()
        self.tmdb_api_key = os.getenv("TMDB_API_KEY", "").strip()
        self.tmdb_region = os.getenv("TMDB_REGION", "IN").strip()

        # Gemini AI
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash").strip()

        # Sarvam AI TTS
        self.sarvam_api_key = (
            os.getenv("SARVAM_API_KEY", "").strip()
            or os.getenv("sarvam_ai_key", "").strip()
        )
        self.sarvam_model = os.getenv("SARVAM_MODEL", "bulbul:v4-flash").strip()
        self.sarvam_speaker = os.getenv("SARVAM_SPEAKER", "vipul_hi_social").strip()

        # Database
        self.database_url = os.getenv("DATABASE_URL", "").strip()
        self.youtube_private_dir = Path(os.getenv("YOUTUBE_PRIVATE_DIR", str(BACKEND_ROOT / ".youtube_private")))
        self.youtube_redirect_uri = os.getenv("YOUTUBE_OAUTH_REDIRECT_URI", "").strip()

        # Media & Directories
        self.storage_dir = os.getenv("STORAGE_DIR", "storage").strip()
        self.ffmpeg_binary = os.getenv("FFMPEG_BINARY", "ffmpeg").strip()
        self.ffprobe_binary = os.getenv("FFPROBE_BINARY", "ffprobe").strip()

        # 9:16 Shorts Video Layout & Appearance
        self.shorts_width = int(os.getenv("SHORTS_WIDTH", "1080"))
        self.shorts_height = int(os.getenv("SHORTS_HEIGHT", "1920"))
        self.shorts_fps = int(os.getenv("SHORTS_FPS", "30"))
        self.shorts_foreground_width_no_crop = int(os.getenv("SHORTS_FOREGROUND_WIDTH_NO_CROP", "1020"))
        self.shorts_foreground_width_with_crop = int(os.getenv("SHORTS_FOREGROUND_WIDTH_WITH_CROP", "1220"))
        self.shorts_foreground_zoom_base = float(os.getenv("SHORTS_FOREGROUND_ZOOM_BASE", "1.50"))
        self.shorts_foreground_zoom_with_crop = float(os.getenv("SHORTS_FOREGROUND_ZOOM_WITH_CROP", "1.70"))
        self.shorts_foreground_brightness = float(os.getenv("SHORTS_FOREGROUND_BRIGHTNESS", "0.06"))
        self.shorts_foreground_contrast = float(os.getenv("SHORTS_FOREGROUND_CONTRAST", "1.08"))
        self.shorts_foreground_saturation = float(os.getenv("SHORTS_FOREGROUND_SATURATION", "1.08"))
        self.shorts_background_blur = int(os.getenv("SHORTS_BACKGROUND_BLUR", "24"))
        self.shorts_background_darkness = float(os.getenv("SHORTS_BACKGROUND_DARKNESS", "-0.08"))

    @property
    def storage_path(self) -> Path:
        p = BACKEND_ROOT / self.storage_dir
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def audio_dir(self) -> Path:
        p = self.storage_path / "audio"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def source_videos_dir(self) -> Path:
        p = self.storage_path / "source_videos"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def thumbnails_dir(self) -> Path:
        p = self.storage_path / "thumbnails"
        p.mkdir(parents=True, exist_ok=True)
        return p

    @property
    def final_videos_dir(self) -> Path:
        p = self.storage_path / "final_videos"
        p.mkdir(parents=True, exist_ok=True)
        return p


settings = Settings()
