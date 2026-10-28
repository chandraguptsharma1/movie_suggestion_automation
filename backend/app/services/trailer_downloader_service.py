import logging
import os
import re
import shutil
import uuid
from pathlib import Path
from typing import Dict, Any, Optional
import yt_dlp
from app.config import settings

logger = logging.getLogger(__name__)


class TrailerDownloaderService:
    def download_trailer(
        self,
        youtube_url: str,
        project_id: int,
        movie_title: str = "trailer",
        label: str = "",
    ) -> Dict[str, Any]:
        safe_title = re.sub(r"[^a-zA-Z0-9_\-]+", "_", movie_title or "trailer")[:30].strip("_") or "trailer"
        file_label = label or f"{safe_title}_{uuid.uuid4().hex[:6]}"
        target_dir = settings.source_videos_dir / f"project_{project_id}"
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / f"{file_label}.mp4"

        # Cookie detection if user provided YOUTUBE_COOKIES env or cookies.txt
        cookie_path: Optional[str] = None
        cookies_env = os.getenv("YOUTUBE_COOKIES", "").strip()
        if cookies_env:
            c_file = Path("/tmp/youtube_cookies.txt")
            try:
                c_file.write_text(cookies_env, encoding="utf-8")
                cookie_path = str(c_file)
            except Exception as e:
                logger.warning("Could not write /tmp/youtube_cookies.txt: %s", e)
        elif Path("cookies.txt").exists():
            cookie_path = "cookies.txt"

        # Let yt-dlp choose supported clients. Forcing mweb without a PO token
        # hides playable formats and fails with "Requested format is not available".
        ydl_opts = {
            "format": "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best[ext=mp4]/best",
            "outtmpl": str(out_path),
            "merge_output_format": "mp4",
            "noplaylist": True,
            "quiet": True,
            "noprogress": True,
            "retries": 2,
            "fragment_retries": 2,
            "extractor_retries": 2,
            "socket_timeout": 15,
        }
        # Node is available locally but yt-dlp only enables Deno by default.
        node_binary = shutil.which("node")
        if node_binary:
            ydl_opts["js_runtimes"] = {"node": {"path": node_binary}}
        if cookie_path:
            ydl_opts["cookiefile"] = cookie_path

        try:
            logger.info("Downloading trailer %s with yt-dlp default clients", youtube_url)
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([youtube_url])
            if not out_path.is_file() or out_path.stat().st_size <= 1000:
                raise RuntimeError("Download did not produce a usable video file.")
            return {
                "success": True,
                "label": file_label,
                "movie_title": movie_title,
                "url": youtube_url,
                "local_path": str(out_path).replace("\\", "/"),
            }
        except Exception as exc:
            logger.warning("Trailer download failed for %s: %s", youtube_url, exc)
            raise RuntimeError(f"Trailer download failed: {exc}") from exc

    def create_cinematic_motion_teaser(
        self,
        image_url: str,
        project_id: int,
        movie_title: str = "Teaser",
        label: str = "",
        duration: int = 6,
    ) -> Dict[str, Any]:
        """
        Creates an ultra-crisp 9:16 cinematic motion video using FFmpeg zoompan from a high-res image (backdrop or poster).
        Provides a 100% reliable cloud fallback when YouTube blocks cloud datacenter IPs.
        """
        import urllib.request
        import subprocess

        safe_title = re.sub(r"[^a-zA-Z0-9_\-]+", "_", movie_title or "movie")[:30].strip("_") or "movie"
        file_label = label or f"motion_{safe_title}_{uuid.uuid4().hex[:6]}"
        target_dir = settings.source_videos_dir / f"project_{project_id}"
        target_dir.mkdir(parents=True, exist_ok=True)
        out_path = target_dir / f"{file_label}.mp4"

        temp_img = target_dir / f"temp_{uuid.uuid4().hex[:6]}.jpg"
        headers = {"User-Agent": "Mozilla/5.0"}
        req = urllib.request.Request(image_url, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp, open(temp_img, "wb") as f:
            f.write(resp.read())

        total_frames = duration * 30
        cmd = [
            settings.ffmpeg_binary,
            "-y",
            "-loop", "1",
            "-i", str(temp_img),
            "-vf", f"scale=1920:1080,zoompan=z='min(zoom+0.0015,1.25)':d={total_frames}:s=1080x1920:fps=30,format=yuv420p",
            "-t", str(duration),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-threads", "2",
            "-pix_fmt", "yuv420p",
            str(out_path),
        ]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        finally:
            if temp_img.exists():
                temp_img.unlink()

        if out_path.exists() and out_path.stat().st_size > 1000:
            logger.info("Generated cinematic motion teaser at %s", out_path)
            return {
                "success": True,
                "label": file_label,
                "movie_title": movie_title,
                "url": f"/storage/source_videos/project_{project_id}/{out_path.name}",
                "local_path": str(out_path).replace("\\", "/"),
                "is_fallback": True,
            }
        raise RuntimeError("Failed to generate cinematic motion teaser video")


trailer_downloader_service = TrailerDownloaderService()
