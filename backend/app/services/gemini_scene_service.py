import json
import hashlib
import math
from io import BytesIO
from PIL import Image, ImageStat
import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

try:
    from google import genai
except ImportError:
    genai = None


def get_video_duration(video_path: str) -> float:
    """Extract precise video duration in seconds using ffprobe."""
    if not os.path.exists(video_path):
        return 0.0

    cmd = [
        settings.ffprobe_binary,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(video_path),
    ]
    try:
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        return float(res.stdout.strip())
    except Exception as exc:
        logger.warning("Could not read duration with ffprobe for %s: %s", video_path, exc)
        return 0.0  # Unknown duration must never produce fabricated timestamps.


def seconds_to_timestamp(seconds: float) -> str:
    """Convert float seconds to HH:MM:SS.mmm format."""
    total_millis = int(round(seconds * 1000))
    hours = total_millis // 3600000
    minutes = (total_millis % 3600000) // 60000
    secs = (total_millis % 60000) // 1000
    millis = total_millis % 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{millis:03d}"


def timestamp_to_seconds(ts: str) -> float:
    """Convert HH:MM:SS or HH:MM:SS.mmm to seconds."""
    parts = ts.strip().split(":")
    if len(parts) == 3:
        h, m, s = parts
        return float(h) * 3600 + float(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return float(m) * 60 + float(s)
    try:
        return float(ts)
    except Exception:
        return 0.0


class GeminiSceneService:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model or "gemini-3.5-flash"

    def _call_gemini_json(self, prompt: str, video_path: Optional[str] = None) -> List[Dict[str, Any]]:
        """Analyze actual uploaded video; never invent visual timestamps from text alone."""
        if not self.api_key or genai is None:
            raise ValueError("GEMINI_API_KEY is not configured.")

        if not video_path or not Path(video_path).is_file():
            raise ValueError("A real trailer file is required for visual scene analysis.")
        client = genai.Client(api_key=self.api_key, http_options={"timeout": 120000})
        uploaded_file = None
        try:
            analysis_path = video_path
            if Path(video_path).stat().st_size > 60 * 1024 * 1024:
                # Preserve timestamps while making large trailers cheap to inspect.
                cache = settings.storage_path / "scene_analysis"
                cache.mkdir(parents=True, exist_ok=True)
                fingerprint = self._source_signature([{"local_path": video_path}])
                proxy = cache / f"{fingerprint}.mp4"
                if not proxy.is_file():
                    subprocess.run([settings.ffmpeg_binary, "-v", "error", "-y", "-i", video_path,
                        "-vf", "scale=640:-2,fps=2", "-an", "-c:v", "libx264", "-preset", "veryfast",
                        "-crf", "30", str(proxy)], capture_output=True, check=True, timeout=180)
                analysis_path = str(proxy)
            uploaded_file = client.files.upload(file=analysis_path)
            for _ in range(60):
                info = client.files.get(name=uploaded_file.name)
                state = getattr(info.state, "name", str(info.state))
                if state == "ACTIVE":
                    uploaded_file = info
                    break
                if state == "FAILED":
                    raise RuntimeError("Gemini could not process this trailer.")
                time.sleep(1)
            else:
                raise TimeoutError("Gemini trailer processing timed out.")

            models = [
                self.model,
                "gemini-3.5-flash",
                "gemini-3.5-flash-lite",
                "gemini-3.1-flash-lite",
                "gemini-3.1-flash-lite-preview",
                "gemini-2.5-flash",
            ]
            seen = set()
            candidate_models = [m for m in models if m and not (m in seen or seen.add(m))]
            last_err = None
            text = ""
            for m in candidate_models:
                try:
                    response = client.models.generate_content(model=m, contents=[uploaded_file, prompt])
                    text = response.text or ""
                    if text:
                        break
                except Exception as exc:
                    logger.warning("Gemini video scene model %s failed: %s", m, exc)
                    last_err = exc
            else:
                raise RuntimeError(f"All Gemini video scene models failed: {last_err}")
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            data = json.loads(text)
            return data.get("scenes", []) if isinstance(data, dict) else data if isinstance(data, list) else []
        finally:
            if uploaded_file:
                try:
                    client.files.delete(name=uploaded_file.name)
                except Exception:
                    logger.warning("Could not remove temporary Gemini analysis file.")
            if hasattr(client, "close"):
                client.close()

    @staticmethod
    def _safe_range(duration):
        if duration < 1:
            return 0.0, 0.0
        start = min(max(1.0, duration * 0.10), duration * 0.25)
        end = min(duration - 0.1, duration * 0.88)
        return start, max(start, end)

    def select_scenes_for_movie(
        self,
        movie_title: str,
        trailer_path: str,
        target_duration: float,
        slot_number: int,
        story_context: str = "",
        why_to_watch: str = "",
    ) -> List[Dict[str, Any]]:
        """
        Uses Gemini to pick short candidate scenes from a single movie trailer
        matching the target spotlight duration without studio logos or end credits.
        """
        trailer_duration = get_video_duration(trailer_path)
        safe_start, safe_end = self._safe_range(trailer_duration)
        if safe_end - safe_start < 1:
            return []
        num_scenes = max(1, min(30, math.ceil(target_duration / 3.5)))

        prompt = f"""You are an elite cinema trailer editor and viral YouTube Shorts creator.
Analyze the 16:9 trailer for the movie: "{movie_title}".

Trailer Total Duration: {round(trailer_duration, 1)} seconds.
Selectable safe range: {round(safe_start, 1)}s to {round(safe_end, 1)}s.
Target total selected footage: {round(target_duration, 1)} seconds across {num_scenes} distinct scenes.

Story Context: {story_context[:250]}
Key Selling Point: {why_to_watch[:200]}

CRITICAL SCENE RULES:
1. NEVER select studio logos, distributor cards, age-rating cards, title cards, or black screens.
2. Select high-energy, eye-catching, action, suspense, or emotional reveal scenes.
3. Each scene MUST be between 2.5 and 5.0 seconds.
4. Total duration of scenes must be very close to {round(target_duration, 1)} seconds.
5. All timestamps MUST be within {round(safe_start, 1)}s and {round(safe_end, 1)}s.
6. Scene types to include: "hook" (opening punchy moment), "story_setup", "danger_suspense", "action_peak".
7. Avoid plot-ending spoilers and repeated shots. Give a diverse sequence of characters, action and story setup.

Return ONLY valid JSON:
```json
[
  {{
    "scene_type": "hook",
    "start": "00:00:15.000",
    "end": "00:00:19.000",
    "duration_seconds": 4.0,
    "visual_energy": "high",
    "reason": "Dramatic character confrontation with intense lighting"
  }}
]
```
"""
        try:
            raw_scenes = self._call_gemini_json(prompt, video_path=trailer_path)
            valid_scenes = []
            for sc in raw_scenes:
                st = timestamp_to_seconds(sc.get("start", "0"))
                en = timestamp_to_seconds(sc.get("end", "0"))
                if st < safe_start:
                    st = safe_start
                if not math.isfinite(st) or not math.isfinite(en):
                    continue
                if en <= st:
                    continue
                en = min(en, safe_end, st + 5.0)
                dur = round(en - st, 2)
                if any(st < s["end_seconds"] and en > s["start_seconds"] for s in valid_scenes):
                    continue
                if dur >= 2.0:
                    valid_scenes.append({
                        "slot": slot_number,
                        "movie_title": movie_title,
                        "source_video_path": trailer_path,
                        "start": seconds_to_timestamp(st),
                        "end": seconds_to_timestamp(en),
                        "start_seconds": round(st, 2),
                        "end_seconds": round(en, 2),
                        "duration_seconds": dur,
                        "scene_type": sc.get("scene_type") or "action_peak",
                        "visual_energy": sc.get("visual_energy") or "high",
                        "reason": sc.get("reason") or f"Scene from {movie_title}",
                        "selection_method": "gemini_video",
                    })

            if valid_scenes:
                return valid_scenes
        except Exception as exc:
            logger.warning("Gemini scene selection call failed for %s: %s. Using visual fallback.", movie_title, exc)

        # Fallback scene generator
        return self._generate_fallback_scenes(
            movie_title=movie_title,
            trailer_path=trailer_path,
            trailer_duration=trailer_duration,
            target_duration=target_duration,
            slot_number=slot_number,
        )

    def _generate_fallback_scenes(
        self,
        movie_title: str,
        trailer_path: str,
        trailer_duration: float,
        target_duration: float,
        slot_number: int,
    ) -> List[Dict[str, Any]]:
        """Use bounded, spread-out timestamps when visual AI analysis is unavailable."""
        safe_start, safe_end = self._safe_range(trailer_duration)
        usable = safe_end - safe_start
        if usable < 1:
            return []
        count = max(1, min(math.ceil(target_duration / 3.5), int(usable / 2) or 1))
        clip_duration = min(5.0, target_duration / count, usable / count)
        scenes = []
        for i in range(count):
            start = safe_start + (usable - clip_duration) * (i / max(1, count - 1))
            end = min(safe_end, start + clip_duration)
            scenes.append({
                "slot": slot_number, "movie_title": movie_title, "source_video_path": trailer_path,
                "start": seconds_to_timestamp(start), "end": seconds_to_timestamp(end),
                "start_seconds": round(start, 3), "end_seconds": round(end, 3),
                "duration_seconds": round(end - start, 3),
                "scene_type": ["hook", "story_setup", "danger_suspense", "action_peak"][i % 4],
                "visual_energy": "unknown", "selection_method": "temporal_fallback",
                "reason": "Time-distributed candidate; scene contents are not AI-verified. Frame quality checked locally.",
            })
        return scenes

    @staticmethod
    def _source_signature(sources):
        rows = []
        for source in sources:
            path = Path(source.get("local_path") or "")
            if path.is_file():
                stat = path.stat()
                rows.append((str(path.resolve()).casefold(), stat.st_size, stat.st_mtime_ns))
        return hashlib.sha256(json.dumps(sorted(set(rows))).encode()).hexdigest()[:20]

    def selection_is_current(self, project):
        signature = self._source_signature(project.get("source_videos_json") or [])
        return any(s.get("source_signature") == signature for s in project.get("scenes_json") or [])

    def _frame_quality(self, path, seconds):
        """Reject black/flat frames and provide a small hash for repeat-shot detection."""
        try:
            result = subprocess.run([settings.ffmpeg_binary, "-v", "error", "-ss", str(seconds),
                "-i", path, "-frames:v", "1", "-vf", "scale=96:54", "-f", "image2pipe",
                "-vcodec", "mjpeg", "pipe:1"], capture_output=True, check=True, timeout=15)
            with Image.open(BytesIO(result.stdout)) as frame:
                gray = frame.convert("L")
                mean = ImageStat.Stat(gray).mean[0]
                deviation = ImageStat.Stat(gray).stddev[0]
                small = list(gray.resize((9, 8)).getdata())
                digest = 0
                for y in range(8):
                    for x in range(8):
                        digest = (digest << 1) | int(small[y * 9 + x] > small[y * 9 + x + 1])
                return mean >= 10 and deviation >= 8, digest
        except Exception:
            return True, None  # Do not reject a real clip solely because a frame probe failed.

    @staticmethod
    def _movie_sources(project, movie, slot):
        entries, seen = [], set()
        for source in project.get("source_videos_json") or []:
            path = source.get("local_path")
            if not path or not Path(path).is_file() or source.get("is_fallback"):
                continue
            title = (source.get("movie_title") or "").strip().casefold()
            matches = (str(source["movie_slot"]) == str(slot) if source.get("movie_slot") is not None
                       else title == movie.get("title", "").strip().casefold())
            if not matches and len(project.get("movies_json") or []) == 1 and not title and source.get("movie_slot") is None:
                matches = True
            normalized = str(Path(path).resolve()).casefold()
            if matches and normalized not in seen:
                seen.add(normalized)
                entries.append(source)
        return entries

    def select_scenes_for_project(self, project: Dict[str, Any]) -> List[Dict[str, Any]]:
        movies = project.get("movies_json") or []
        spotlights = (project.get("script_data_json") or {}).get("movie_spotlights") or []
        voice_duration = get_video_duration(project.get("voice_audio_path") or "")
        durations = []
        for index, movie in enumerate(movies, 1):
            spotlight = next((s for s in spotlights if str(s.get("slot")) == str(index)), {})
            durations.append(max(1.0, float(spotlight.get("duration_sec") or (45 if len(movies) == 1 else 16))))
        total = sum(durations)
        signature = self._source_signature(project.get("source_videos_json") or [])
        all_scenes = []
        for slot, movie in enumerate(movies, 1):
            title = movie.get("title") or f"Movie {slot}"
            sources = self._movie_sources(project, movie, slot)
            if not sources:
                raise ValueError(f"No usable downloaded trailer found for {title}. Download its trailer first.")
            target = voice_duration * durations[slot - 1] / total if voice_duration > 0 else durations[slot - 1]
            spotlight = next((s for s in spotlights if str(s.get("slot")) == str(slot)), {})
            groups = []
            for trailer_index, source in enumerate(sources, 1):
                path = source["local_path"]
                candidate_target = target / len(sources) + 5  # Spare candidates allow weak/repeated shots to be skipped.
                candidates = self.select_scenes_for_movie(title, path, candidate_target, slot,
                    spotlight.get("story_premise") or movie.get("overview", ""), spotlight.get("why_to_watch", ""))
                if sum(s["duration_seconds"] for s in candidates) < candidate_target:
                    candidates.extend(self._generate_fallback_scenes(title, path, get_video_duration(path),
                                      candidate_target * 1.5, slot))
                for candidate in candidates:
                    candidate.update(source_label=source.get("source_label") or source.get("label") or f"Trailer {trailer_index}",
                        source_url=source.get("origin_url") or source.get("url") or "", trailer_index=trailer_index,
                        source_signature=signature)
                # Prefer AI's high-energy candidates; retain chronological variety within each source.
                candidates.sort(key=lambda s: (s.get("selection_method") != "gemini_video",
                    s.get("scene_type") != "hook", s.get("visual_energy") != "high", s["start_seconds"]))
                groups.append(candidates)
            selected, hashes = [], []
            used = 0.0
            while used < target - 0.05 and any(groups):
                made_progress = False
                for group in groups:
                    while group and used < target - 0.05:
                        candidate = dict(group.pop(0))
                        if any(s["source_video_path"] == candidate["source_video_path"] and
                               candidate["start_seconds"] < s["end_seconds"] and
                               candidate["end_seconds"] > s["start_seconds"] for s in selected):
                            continue
                        good, digest = self._frame_quality(candidate["source_video_path"],
                            (candidate["start_seconds"] + candidate["end_seconds"]) / 2)
                        if not good or (digest is not None and any((digest ^ old).bit_count() <= 5 for old in hashes)):
                            continue
                        length = min(5.0, candidate["duration_seconds"], target - used)
                        if length < 0.5:
                            continue
                        candidate["end_seconds"] = round(candidate["start_seconds"] + length, 3)
                        candidate["end"] = seconds_to_timestamp(candidate["end_seconds"])
                        candidate["duration_seconds"] = round(length, 3)
                        candidate["quality_checked"] = digest is not None
                        selected.append(candidate)
                        used += length
                        if digest is not None:
                            hashes.append(digest)
                        made_progress = True
                        break  # Alternate trailers instead of exhausting the first one.
                if not made_progress:
                    break
            if not selected:
                raise ValueError(f"No usable scenes remain for {title}; try different trailers.")
            if used < target - 0.5:
                logger.warning("Selected %.1fs of %.1fs for %s after quality/repeat checks.", used, target, title)
            all_scenes.extend(selected)
        return all_scenes


gemini_scene_service = GeminiSceneService()
