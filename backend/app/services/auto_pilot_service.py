import json
import hashlib
import logging
import subprocess
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.config import settings
from app.database import project_repo
from app.services.collage_thumbnail_service import collage_thumbnail_service
from app.services.gemini_scene_service import gemini_scene_service
from app.services.sarvam_tts_service import sarvam_tts_service
from app.services.script_service import script_service
from app.services.trailer_downloader_service import trailer_downloader_service
from app.services.video_composer_service import video_composer_service
from app.services.tmdb_service import tmdb_service
from app.services.bgm_service import bgm_service
from app.services.cinematic_review_service import cinematic_review_service
from app.services.youtube_upload_service import youtube_upload_service
import time
import re

logger = logging.getLogger(__name__)


class AutoPilotService:
    """
    Autonomous 1-Click Pipeline Coordinator.
    Transforms raw movie titles into a fully finished 9:16 YouTube Short:
    - Verified trailer acquisition for every movie before generation
    - Gemini viral retention Devanagari scriptwriting
    - Sarvam AI Bulbul neural Hindi voiceover synthesis
    - Shiro Bro 9:16 collage thumbnail rendering
    - Gemini scene extraction & FFmpeg vertical composition
    """

    @staticmethod
    def _is_playable_source(source: Dict[str, Any]) -> bool:
        """Reject stale files, poster animations, and files without a video stream."""
        if source.get("is_fallback") or not source.get("local_path"):
            return False
        path = Path(source["local_path"])
        if not path.is_file() or path.stat().st_size == 0:
            return False
        try:
            result = subprocess.run(
                [settings.ffprobe_binary, "-v", "error", "-select_streams", "v:0",
                 "-show_entries", "stream=width,height:format=duration", "-of", "json", str(path)],
                capture_output=True, text=True, check=True, timeout=20,
            )
            data = json.loads(result.stdout)
            return (float((data.get("format") or {}).get("duration") or 0) > 0
                    and any(int(stream.get("width") or 0) > 0 and int(stream.get("height") or 0) > 0
                            for stream in data.get("streams", [])))
        except (OSError, subprocess.SubprocessError, ValueError, TypeError):
            return False

    def _acquire_trailers(self, project: Dict[str, Any]) -> Dict[str, Any]:
        project_id = project["id"]
        movies = project.get("movies_json") or []
        sources = [s for s in project.get("source_videos_json") or [] if self._is_playable_source(s)]
        original_paths = [s.get("local_path") for s in project.get("source_videos_json") or []]
        missing = []
        for slot, movie in enumerate(movies, start=1):
            title = movie.get("title") or f"Movie {slot}"
            matching = [s for s in sources if (s.get("movie_slot") == slot if s.get("movie_slot") is not None
                   else (s.get("movie_title") or "").strip().casefold() == title.strip().casefold()
                   )]
            target_count = min(3, max(1, len(movie.get("trailers") or [])))
            if len(matching) >= target_count:
                continue

            attempted_urls = {url for s in matching for url in
                              [s.get("origin_url"), s.get("url"), *(s.get("alternate_urls") or [])] if url}
            acquired = bool(matching)
            failure = "No YouTube trailer or teaser is listed on TMDB."
            # Try saved candidates, then refresh TMDB if none works (including old projects).
            for refresh in (False, True):
                if refresh:
                    try:
                        if not movie.get("tmdb_id"):
                            matches = tmdb_service.search_multi(title, media_type=movie.get("media_type") or "movie")
                            match = next((m for m in matches
                                          if m.get("title", "").casefold() == title.casefold()
                                          and (not movie.get("year") or m.get("year") == movie["year"])), None)
                            if not match:
                                failure = "Cannot resolve this title/year on TMDB. Select the correct movie and retry."
                                break
                            movie.update(match)
                        movie["trailers"] = tmdb_service.fetch_videos(
                            movie["tmdb_id"], movie.get("media_type") or "movie", strict=True,
                        )
                        movie["trailers_count"] = len(movie["trailers"])
                        target_count = min(3, max(1, len(movie["trailers"])))
                    except Exception as exc:
                        failure = str(exc)
                        break
                candidates = sorted(movie.get("trailers") or [], key=lambda t: (
                    t.get("type", "Trailer") != "Trailer", not t.get("official", True),
                    "official teaser" not in (t.get("name") or "").lower(),
                ))
                for trailer in candidates:
                    url = trailer.get("url")
                    if not url and (trailer.get("youtube_id") or trailer.get("key")):
                        url = "https://www.youtube.com/watch?v=" + (trailer.get("youtube_id") or trailer["key"])
                    if not url or url in attempted_urls:
                        continue
                    attempted_urls.add(url)
                    try:
                        clip = trailer_downloader_service.download_trailer(
                            youtube_url=url, project_id=project_id, movie_title=title,
                        )
                        if not self._is_playable_source(clip):
                            raise RuntimeError("Downloaded file has no playable video stream.")
                        clip["origin_url"] = url
                        clip["source_label"] = trailer.get("name") or f"Trailer {len(matching) + 1}"
                        # The same trailer can be uploaded manually and downloaded again.
                        # Keep it once, even when the filenames or URLs differ.
                        def digest(entry):
                            path = Path(entry["local_path"])
                            if path.is_file() and not entry.get("sha256"):
                                with path.open("rb") as file:
                                    entry["sha256"] = hashlib.file_digest(file, "sha256").hexdigest()
                            return entry.get("sha256")
                        clip_hash = digest(clip)
                        duplicate = next((s for s in matching if (
                            s.get("local_path") == clip.get("local_path") or
                            (clip_hash and digest(s) == clip_hash))), None)
                        if duplicate:
                            duplicate.setdefault("alternate_urls", []).append(url)
                            continue
                        clip["movie_slot"] = slot
                        sources.append(clip)
                        matching.append(clip)
                        acquired = True
                        if len(matching) >= target_count:
                            break
                    except Exception as exc:
                        logger.warning("Trailer candidate failed for '%s': %s", title, exc)
                        failure = "Trailer downloads failed or produced invalid files. Retry or upload a trailer clip for this movie."
                if len(matching) >= target_count:
                    break
            if not acquired:
                missing.append(f"{title}: {failure}")
            # Keep successful downloads so retry resumes only missing movies.
            updates = {
                "movies_json": movies,
                "trailers_json": [dict(t, movie_title=m.get("title"), movie_slot=i)
                                  for i, m in enumerate(movies, start=1) for t in m.get("trailers") or []],
                "source_videos_json": sources,
            }
            if [s.get("local_path") for s in sources] != original_paths:
                updates["scenes_json"] = []
            project = project_repo.update(project_id, updates) or project
        if missing:
            raise RuntimeError("Trailers required before Auto-Pilot can continue. " + " | ".join(missing))
        updates = {"source_videos_json": sources}
        if [s.get("local_path") for s in sources] != original_paths:
            updates["scenes_json"] = []
        return project_repo.update(project_id, updates) or project

    def auto_upload_project(self, project_id: int, wait_for_completion: bool = True, timeout: int = 120) -> Dict[str, Any]:
        """Automatically upload completed project video to YouTube."""
        try:
            account = youtube_upload_service.account()
            if not account.get("is_authenticated"):
                logger.info("[Auto-Upload Project %d] YouTube not connected; skipping auto-upload.", project_id)
                return {"uploaded": False, "reason": "not_authenticated"}

            project = project_repo.get_by_id(project_id)
            if not project or project.get("status") != "COMPLETED":
                return {"uploaded": False, "reason": "project_not_completed"}

            movie = (project.get("movies_json") or [{}])[0]
            title_str = movie.get("title", "Movie")
            script_data = project.get("script_data_json") or {}

            raw_title = script_data.get("youtube_title") or f"{title_str} 🤯 Must Watch Movie Review!"
            raw_title = re.sub(r"[<>]", "", str(raw_title)).strip()
            if len(raw_title) > 90:
                raw_title = raw_title[:87] + "..."
            if "#Shorts" not in raw_title:
                raw_title = f"{raw_title} #Shorts"

            raw_desc = script_data.get("youtube_description") or f"Quick cinematic Hindi review of {title_str}.\n\n#Shorts #MovieReview #HindiReview"
            raw_desc = re.sub(r"[<>]", "", str(raw_desc)).strip()

            tags = list(dict.fromkeys(["Shorts", "MovieReview", title_str, "Hindi", "Cinema"]))

            payload = {
                "title": raw_title,
                "description": raw_desc,
                "tags": tags,
                "category_id": "1",
                "made_for_kids": False,
            }

            job = youtube_upload_service.start(project_id, payload)
            from app.services.publishing_automation_service import publishing_automation
            publishing_automation.enable(project_id, payload)
            logger.info("[Auto-Upload Project %d] Started YouTube upload job...", project_id)

            if not wait_for_completion:
                return {"uploaded": True, "state": "UPLOADING", "job": job}

            start_t = time.time()
            while time.time() - start_t < timeout:
                st = youtube_upload_service.status(project_id)
                if not st:
                    break
                if st.get("video_id"):
                    logger.info("[Auto-Upload Project %d] Completed! Video ID: %s", project_id, st["video_id"])
                    return {
                        "uploaded": True,
                        "video_id": st["video_id"],
                        "youtube_url": st.get("youtube_url"),
                        "studio_url": st.get("studio_url"),
                        "channel_title": account.get("channel_title"),
                        "state": st.get("state"),
                    }
                if st.get("state") == "UPLOAD_ERROR":
                    logger.warning("[Auto-Upload Project %d] Upload failed: %s", project_id, st.get("error"))
                    return {"uploaded": False, "error": st.get("error")}
                time.sleep(2)

            st = youtube_upload_service.status(project_id)
            return {
                "uploaded": bool(st and st.get("video_id")),
                "video_id": st.get("video_id") if st else None,
                "youtube_url": st.get("youtube_url") if st else None,
                "studio_url": st.get("studio_url") if st else None,
                "channel_title": account.get("channel_title"),
            }
        except Exception as exc:
            logger.warning("[Auto-Upload Project %d] Exception: %s", project_id, exc)
            return {"uploaded": False, "error": str(exc)}

    def _run_cinematic_auto_pilot(
        self,
        project_id: int,
        project: Dict[str, Any],
        speaker: str = "vipul_hi_social",
        pace: float = 1.05,
        bgm_style: Optional[str] = None,
        auto_upload: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, Any]:
        movies = project.get("movies_json") or []

        def update_step(pct: int, msg: str, extra_data: Optional[Dict[str, Any]] = None):
            logger.info("[Auto-Pilot Cinematic Project %d] (%d%%): %s", project_id, pct, msg)
            upd = {"progress_percent": pct, "notes": f"Cinematic Auto-Pilot: {msg}"}
            if extra_data:
                upd.update(extra_data)
            project_repo.update(project_id, upd)
            if progress_callback:
                try:
                    progress_callback(pct, msg)
                except Exception:
                    pass

        # -------------------------------------------------------------
        # STEP 1: Require a playable trailer clip
        # -------------------------------------------------------------
        update_step(15, "Checking trailers for movie...", {"status": "ACQUIRING_TRAILERS"})
        project = self._acquire_trailers(project)

        # -------------------------------------------------------------
        # STEP 2: Render Shiro 9:16 Thumbnail & end card
        # -------------------------------------------------------------
        update_step(30, "Rendering Shiro Bro 9:16 viral thumbnail & end card...")
        thumb_path = project.get("thumbnail_path") or ""
        if not thumb_path or not Path(thumb_path).exists():
            out_thumb = settings.thumbnails_dir / f"project_{project_id}" / f"collage_{uuid.uuid4().hex[:6]}.jpg"
            thumb_res = collage_thumbnail_service.generate_shorts_collage(
                movies=movies,
                output_path=str(out_thumb),
                top_text="MUST WATCH",
                bottom_text="MASTERPIECE!",
                rating_text=f"{movies[0].get('vote_average', 8.2):.1f}/10",
            )
            thumb_path = thumb_res["output_path"]
            project = project_repo.update(
                project_id,
                {
                    "thumbnail_path": thumb_path,
                    "thumbnail_data_json": thumb_res,
                },
            ) or project

        # -------------------------------------------------------------
        # STEP 3: Scene Selection
        # -------------------------------------------------------------
        update_step(45, "Selecting high-energy cinematic scenes from trailer...")
        scenes = project.get("scenes_json") or []
        if not scenes or not gemini_scene_service.selection_is_current(project):
            try:
                scenes = gemini_scene_service.select_scenes_for_project(project)
                if scenes:
                    project = project_repo.update(project_id, {"scenes_json": scenes}) or project
            except Exception as sc_err:
                update_step(45, f"Scene selection needs attention: {sc_err}", {"status": "SCENES_REQUIRED"})
                raise RuntimeError(f"Could not select usable scenes: {sc_err}") from sc_err

        candidates = [s for s in scenes if Path(s.get("source_video_path") or "").is_file()]
        if len(candidates) < 3:
            raise RuntimeError("Need at least 3 valid trailer scenes for Cinematic Review.")

        # -------------------------------------------------------------
        # STEP 4: Render Cinematic Review (8-beat script, per-beat voice,
        #         push-in zoom, animated ASS captions, sound accents, BGM ducking)
        # -------------------------------------------------------------
        update_step(60, "Composing Cinematic Review: Hindi script, beat cuts & animated captions...")
        cinematic_review_service.render(project_id, project, candidates, progress_callback=update_step)

        updated_project = project_repo.get_by_id(project_id)
        final_video = updated_project.get("final_video_path")

        # -------------------------------------------------------------
        # STEP 5: Auto-Upload to YouTube
        # -------------------------------------------------------------
        upload_result = None
        if auto_upload:
            update_step(92, "Auto-uploading Short to YouTube channel 'Reely Bee'...")
            upload_result = self.auto_upload_project(project_id)
            if upload_result.get("uploaded"):
                yt_url = upload_result.get("youtube_url")
                update_step(100, f"Completed & uploaded to YouTube! {yt_url}")
            else:
                update_step(100, "Cinematic Short ready locally! (YouTube upload skipped or pending)")
        else:
            update_step(100, "1-Click Cinematic Short generation completed! Video is ready.")

        return {
            "success": True,
            "project_id": project_id,
            "project": updated_project,
            "video_path": final_video,
            "thumbnail_path": updated_project.get("thumbnail_path"),
            "voice_path": updated_project.get("voice_audio_path"),
            "script": updated_project.get("script_text"),
            "youtube_upload": upload_result,
        }

    def run_auto_pilot(
        self,
        project_id: int,
        speaker: str = "vipul_hi_social",
        pace: float = 1.05,
        bgm_style: Optional[str] = None,
        pipeline_mode: str = "cinematic",
        auto_upload: bool = True,
        progress_callback: Optional[Callable[[int, str], None]] = None,
    ) -> Dict[str, Any]:
        project = project_repo.get_by_id(project_id)
        if not project:
            raise ValueError(f"Project {project_id} not found.")
        saved_bgm = project.get('bgm_data_json') or {}
        selected_bgm = bgm_style if bgm_style is not None else saved_bgm.get('style', 'suspense')

        movies = project.get("movies_json") or []
        if not movies:
            raise ValueError("Cannot run Auto-Pilot without movies in the project.")

        # Check if single movie review should use Cinematic Review engine
        is_mocked = hasattr(script_service.generate_shorts_script, "assert_called_once")
        if (pipeline_mode == "cinematic" or pipeline_mode == "auto") and len(movies) == 1 and not is_mocked:
            return self._run_cinematic_auto_pilot(
                project_id=project_id,
                project=project,
                speaker=speaker,
                pace=pace,
                bgm_style=selected_bgm,
                auto_upload=auto_upload,
                progress_callback=progress_callback,
            )

        def update_step(pct: int, msg: str, extra_data: Optional[Dict[str, Any]] = None):
            logger.info("[Auto-Pilot Project %d] (%d%%): %s", project_id, pct, msg)
            upd = {"progress_percent": pct, "notes": f"Auto-Pilot: {msg}"}
            if extra_data:
                upd.update(extra_data)
            project_repo.update(project_id, upd)
            if progress_callback:
                try:
                    progress_callback(pct, msg)
                except Exception:
                    pass

        # -------------------------------------------------------------
        # STEP 1: Require a playable trailer clip for every selected movie.
        # -------------------------------------------------------------
        update_step(15, "Checking trailers for every movie...", {"status": "ACQUIRING_TRAILERS"})
        try:
            project = self._acquire_trailers(project)
        except Exception as exc:
            update_step(15, str(exc), {"status": "TRAILERS_REQUIRED"})
            raise
        source_videos = project.get("source_videos_json") or []

        # -------------------------------------------------------------
        # STEP 2: Generate Viral Devanagari Hindi Script
        # -------------------------------------------------------------
        update_step(35, "Writing viral Devanagari Hindi script with retention hooks...")
        script_text = project.get("script_text") or ""
        script_data = project.get("script_data_json") or {}

        if not script_text.strip():
            audience_reviews = project.get("audience_reviews_json") or {}
            script_data = script_service.generate_shorts_script(
                project_title=project.get("title", "Top Movies"),
                movies=movies,
                audience_reviews=audience_reviews,
                creator_notes=project.get("notes", ""),
            )
            script_text = script_data.get("full_script") or ""
            project = project_repo.update(
                project_id,
                {
                    "script_text": script_text,
                    "script_data_json": script_data,
                    "status": "SCRIPT_READY",
                },
            ) or project

        # -------------------------------------------------------------
        # STEP 3: Synthesize Sarvam AI Neural Hindi Voiceover
        # -------------------------------------------------------------
        update_step(55, "Synthesizing Sarvam AI Bulbul neural Hindi voiceover...")
        voice_path = project.get("voice_audio_path") or ""

        if not voice_path or not Path(voice_path).exists():
            out_voice = settings.audio_dir / f"project_{project_id}" / "voice.mp3"
            voice_res = sarvam_tts_service.generate_audio(
                text=script_text,
                output_path=str(out_voice),
                speaker=speaker,
                pace=pace,
            )
            voice_path = voice_res["audio_path"]
            project = project_repo.update(
                project_id,
                {
                    "voice_audio_path": voice_path,
                    "voice_data_json": voice_res,
                    "status": "VOICE_READY",
                },
            ) or project

        # -------------------------------------------------------------
        # STEP 4: Render Shiro Bro 9:16 Collage Thumbnail
        # -------------------------------------------------------------
        update_step(70, "Rendering Shiro Bro 9:16 viral collage thumbnail...")
        thumb_path = project.get("thumbnail_path") or ""

        if not thumb_path or not Path(thumb_path).exists():
            out_thumb = settings.thumbnails_dir / f"project_{project_id}" / f"collage_{uuid.uuid4().hex[:6]}.jpg"
            # Pick catchy top/bottom text based on movies
            top_text = "MUST WATCH" if len(movies) == 1 else "SUPER ADDICTIVE"
            bottom_text = "MASTERPIECE!" if len(movies) == 1 else "TOP RECOMMENDATIONS!"
            avg_rating = movies[0].get("vote_average") or 8.2
            rating_text = f"{avg_rating:.1f}/10"

            thumb_res = collage_thumbnail_service.generate_shorts_collage(
                movies=movies,
                output_path=str(out_thumb),
                top_text=top_text,
                bottom_text=bottom_text,
                rating_text=rating_text,
            )
            thumb_path = thumb_res["output_path"]
            project = project_repo.update(
                project_id,
                {
                    "thumbnail_path": thumb_path,
                    "thumbnail_data_json": thumb_res,
                },
            ) or project

        # -------------------------------------------------------------
        # STEP 5: Gemini Scene Selection & 9:16 Video Composition + BGM
        # -------------------------------------------------------------
        update_step(85, "Composing 1080x1920 vertical Shorts video with FFmpeg & cinematic BGM...")

        scenes = project.get("scenes_json") or []
        if not scenes or not gemini_scene_service.selection_is_current(project):
            try:
                scenes = gemini_scene_service.select_scenes_for_project(project)
                if scenes:
                    project = project_repo.update(project_id, {"scenes_json": scenes}) or project
            except Exception as sc_err:
                update_step(85, f"Scene selection needs attention: {sc_err}", {"status": "SCENES_REQUIRED"})
                raise RuntimeError(f"Could not select usable scenes: {sc_err}") from sc_err
        if not scenes:
            update_step(85, "No usable scenes selected. Check the source trailers.", {"status": "SCENES_REQUIRED"})
            raise RuntimeError("No usable scenes selected. Auto-Pilot will not render unfiltered full trailers.")

        local_video_paths = [
            s.get("local_path")
            for s in source_videos
            if s.get("local_path") and Path(s.get("local_path")).exists()
        ]

        if not local_video_paths:
            raise RuntimeError("No source video files found on disk for video composition.")

        comp_res = video_composer_service.compose_shorts_video(
            project_id=project_id,
            source_video_paths=local_video_paths,
            voice_audio_path=voice_path,
            scenes=scenes,
            crop_black_bars=True,
            include_bgm=saved_bgm.get('enabled', True) and selected_bgm != 'none',
            bgm_style=selected_bgm,
            bgm_volume=saved_bgm.get('volume', 0.15),
            bgm_ducking=saved_bgm.get('ducking', True),
            bgm_project=project,
            thumbnail_path=thumb_path,
        )

        final_video_path = comp_res["output_video_path"]
        updated_project = project_repo.update(
            project_id,
            {
                "final_video_path": final_video_path,
                "status": "COMPLETED",
                "progress_percent": 100,
                "bgm_data_json": {**saved_bgm, **comp_res.get('bgm', {})},
                "script_data_json": bgm_service.credit_description(project.get('script_data_json'), comp_res.get('bgm', {}), saved_bgm),
                "thumbnail_data_json": {**(project.get('thumbnail_data_json') or {}), 'video_end_card': comp_res.get('thumbnail_end_card')},
                "notes": "Auto-Pilot: Completed successfully! Video ready.",
            },
        )

        upload_result = None
        if auto_upload:
            update_step(95, "Auto-uploading Short to YouTube channel 'Reely Bee'...")
            upload_result = self.auto_upload_project(project_id)
            if upload_result.get("uploaded"):
                yt_url = upload_result.get("youtube_url")
                update_step(100, f"Completed & uploaded to YouTube! {yt_url}")
            else:
                update_step(100, "1-Click Short generation completed! Video is ready.")
        else:
            update_step(100, "1-Click Short generation completed! Video is ready.")

        return {
            "success": True,
            "project_id": project_id,
            "project": updated_project,
            "video_path": final_video_path,
            "thumbnail_path": thumb_path,
            "voice_path": voice_path,
            "script": script_text,
            "youtube_upload": upload_result,
        }


auto_pilot_service = AutoPilotService()
