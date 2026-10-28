import json
import logging
import os
import re
import subprocess
from pathlib import Path
from uuid import uuid4
from typing import Dict, Any, List, Optional, Tuple
from app.config import settings
from app.services.bgm_service import bgm_service

logger = logging.getLogger(__name__)


class VideoComposerService:
    @staticmethod
    def _ffmpeg_error(stderr):
        text = stderr.decode('utf-8', errors='replace') if isinstance(stderr, bytes) else str(stderr or '')
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        relevant = [line for line in lines if re.search(r'error|invalid|failed|cannot|no such|permission denied|not divisible|unable', line, re.I)]
        return '\n'.join(relevant[-10:] or lines[-8:])[-2400:] or 'FFmpeg exited without an error message.'

    def _layout_for_source(self, source, crop_black_bars, foreground_zoom, foreground_width):
        width, height = self._probe_video_dimensions(source)
        crop = self.detect_crop_area(source) if crop_black_bars else {
            'original_width': width, 'original_height': height, 'crop_w': width, 'crop_h': height,
            'crop_applied': False, 'crop_method': 'none', 'crop_x': 0, 'crop_y': 0,
        }
        cropped = crop.get('crop_applied')
        return self.build_shorts_filter_graph(crop_info=crop,
            shorts_width=settings.shorts_width, shorts_height=settings.shorts_height,
            foreground_width=foreground_width if foreground_width is not None else (
                settings.shorts_foreground_width_with_crop if cropped else settings.shorts_foreground_width_no_crop),
            foreground_zoom=foreground_zoom if foreground_zoom is not None else (
                settings.shorts_foreground_zoom_with_crop if cropped else settings.shorts_foreground_zoom_base),
            background_blur=settings.shorts_background_blur, background_darkness=settings.shorts_background_darkness,
            foreground_brightness=settings.shorts_foreground_brightness, foreground_contrast=settings.shorts_foreground_contrast,
            foreground_saturation=settings.shorts_foreground_saturation)

    @staticmethod
    def _end_card_filter(image_index, content_duration, width, height, fps, seconds=2.0):
        return (
            f"[v]trim=duration={content_duration:.6f},setpts=PTS-STARTPTS,fps={fps},setsar=1,format=yuv420p[content];"
            f"[{image_index}:v]scale={width}:{height}:force_original_aspect_ratio=decrease,"
            f"pad={width}:{height}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1,fps={fps},"
            f"format=yuv420p,trim=duration={seconds},setpts=PTS-STARTPTS[endcard];"
            "[content][endcard]concat=n=2:v=1:a=0[vfinal]"
        )

    def append_thumbnail_end_card(self, video_path, thumbnail_path, output_path, content_duration=None):
        """Add a selectable ending frame to an already mixed Short, preserving its full content."""
        if not Path(video_path).is_file() or not Path(thumbnail_path).is_file():
            raise ValueError("Video or thumbnail file is missing.")
        if Path(video_path).resolve() == Path(output_path).resolve():
            raise ValueError("End-card output must be different from the input video.")
        duration = self._probe_video_duration(str(video_path))
        if content_duration is not None:
            if not 0 < float(content_duration) <= duration:
                raise ValueError('Invalid end-card start time')
            duration = float(content_duration)
        width, height = self._probe_video_dimensions(str(video_path))
        total = duration + 2.0
        graph = (f"[0:v]fps={settings.shorts_fps},setsar=1,format=yuv420p[v];" +
                 self._end_card_filter(1, duration, width, height, settings.shorts_fps) +
                 f";[0:a]apad=pad_dur=2,atrim=duration={total:.6f}[afinal]")
        subprocess.run([settings.ffmpeg_binary, "-v", "error", "-nostdin", "-y", "-i", str(video_path),
            "-loop", "1", "-framerate", str(settings.shorts_fps), "-i", str(thumbnail_path),
            "-filter_complex", graph, "-filter_complex_threads", "1", "-map", "[vfinal]", "-map", "[afinal]",
            "-t", str(total), "-c:v", "libx264", "-preset", "ultrafast", "-crf", "20", "-threads", "2",
            "-c:a", "aac", "-b:a", "192k", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(output_path)],
            capture_output=True, check=True)
        return {"path": str(thumbnail_path), "starts_at_seconds": duration, "duration_seconds": 2.0,
                "output_video_path": str(output_path).replace('\\', '/')}

    def _probe_video_dimensions(self, video_path: str) -> Tuple[int, int]:
        """Probe width and height of a video file using ffprobe."""
        cmd = [
            settings.ffprobe_binary,
            "-v",
            "error",
            "-select_streams",
            "v:0",
            "-show_entries",
            "stream=width,height",
            "-of",
            "json",
            str(video_path),
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            data = json.loads(res.stdout)
            streams = data.get("streams") or []
            if streams:
                return int(streams[0].get("width", 1920)), int(streams[0].get("height", 1080))
        except Exception as exc:
            logger.warning("Could not probe video dimensions for %s: %s", video_path, exc)
        return 1920, 1080

    def _probe_video_duration(self, video_path: str) -> float:
        """Probe duration of a video file in seconds."""
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
            return max(0.1, float(res.stdout.strip()))
        except Exception:
            return 10.0

    def _run_cropdetect(
        self,
        video_path: str,
        sample_duration: float = 10.0,
        limit: float = 0.08,
        start_offset: float = 2.0,
    ) -> Optional[Tuple[int, int, int, int]]:
        """Run FFmpeg cropdetect filter to find letterbox black bars."""
        cmd = [
            settings.ffmpeg_binary,
            "-hide_banner",
            "-ss",
            f"{start_offset:.3f}",
            "-t",
            f"{sample_duration:.3f}",
            "-i",
            str(video_path),
            "-vf",
            f"cropdetect=limit={limit}:round=2:reset=0",
            "-an",
            "-f",
            "null",
            "-",
        ]
        try:
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = (res.stderr or "") + "\n" + (res.stdout or "")
            matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", output)
            if matches:
                return tuple(int(v) for v in matches[-1])
        except Exception as exc:
            logger.warning("cropdetect failed for %s: %s", video_path, exc)
        return None

    def detect_crop_area(self, video_path: str) -> Dict[str, Any]:
        """
        Detects top and bottom black bars in movie trailers / clips.
        Returns crop coordinates (crop_w, crop_h, crop_x, crop_y) and crop_method.
        """
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video not found: {video_path}")

        orig_w, orig_h = self._probe_video_dimensions(video_path)
        default_result = {
            "detected": False,
            "original_width": orig_w,
            "original_height": orig_h,
            "has_black_bars": False,
            "crop_applied": False,
            "crop_method": "none",
            "crop_w": orig_w,
            "crop_h": orig_h,
            "crop_x": 0,
            "crop_y": 0,
        }

        # Try cropdetect with limit=0.08 then 0.03
        crop_res = self._run_cropdetect(video_path, sample_duration=8.0, limit=0.08, start_offset=3.0)
        if not crop_res:
            crop_res = self._run_cropdetect(video_path, sample_duration=6.0, limit=0.03, start_offset=1.5)

        if crop_res:
            crop_w, crop_h, crop_x, crop_y = crop_res
            # Validate crop boundaries
            if 0 < crop_w <= orig_w and 0 < crop_h <= orig_h and crop_x >= 0 and crop_y >= 0:
                height_diff = orig_h - crop_h
                # Check if letterbox bars are significant (> 24px or > 6% of height)
                if height_diff >= max(24, int(orig_h * 0.06)):
                    crop_x = 0 if abs(crop_x) <= 6 else crop_x
                    crop_w = orig_w if abs(orig_w - crop_w) <= 12 else crop_w
                    return {
                        "detected": True,
                        "original_width": orig_w,
                        "original_height": orig_h,
                        "crop_w": crop_w,
                        "crop_h": crop_h,
                        "crop_x": crop_x,
                        "crop_y": crop_y,
                        "has_black_bars": True,
                        "crop_applied": True,
                        "crop_method": "cropdetect",
                        "crop_expression": f"{crop_w}:{crop_h}:{crop_x}:{crop_y}",
                    }

        # If video is already vertical or square, never crop letterbox bars
        if orig_w <= orig_h or (orig_w / max(orig_h, 1)) < 1.2:
            return default_result

        # If standard cinematic widescreen (2.35:1 or 2.39:1 letterbox) is likely
        # Fallback safe letterbox crop (cuts 13% top, 13% bottom, keeping center 74%)
        fallback_h = int(round(orig_h * 0.74))
        if fallback_h % 2 != 0:
            fallback_h -= 1
        fallback_y = int(round(orig_h * 0.13))
        if fallback_y % 2 != 0:
            fallback_y -= 1

        return {
            "detected": True,
            "original_width": orig_w,
            "original_height": orig_h,
            "crop_w": orig_w,
            "crop_h": fallback_h,
            "crop_x": 0,
            "crop_y": fallback_y,
            "has_black_bars": True,
            "crop_applied": True,
            "crop_method": "fallback",
            "crop_expression": "in_w:in_h*0.74:0:in_h*0.13",
        }

    def _cut_scene_segment(
        self,
        source_path: str,
        start_sec: float,
        dur_sec: float,
        out_segment_path: Path,
        crop_black_bars: bool = True,
        layout_filter: Optional[str] = None,
    ) -> bool:
        """Cut a single scene clip, optionally cropping letterbox bars and standardizing for composition."""
        if not os.path.exists(source_path):
            return False

        orig_w, orig_h = self._probe_video_dimensions(source_path)
        v_dur = self._probe_video_duration(source_path)

        # If requested start_sec is beyond or near the end of the video, loop back to 0
        if start_sec < 0 or start_sec >= v_dur or dur_sec <= 0:
            return False
        dur_sec = min(dur_sec, max(1.0, v_dur - start_sec))

        is_vertical = orig_w <= orig_h or (orig_w / max(orig_h, 1)) < 1.0

        vf_parts = []
        if is_vertical:
            vf_parts.append(f"scale={settings.shorts_width}:{settings.shorts_height}:force_original_aspect_ratio=increase")
            vf_parts.append(f"crop={settings.shorts_width}:{settings.shorts_height}")
        else:
            if crop_black_bars:
                crop_info = self.detect_crop_area(source_path)
                if crop_info.get("crop_applied"):
                    if crop_info.get("crop_method") == "fallback":
                        vf_parts.append("crop=in_w:in_h*0.74:0:in_h*0.13")
                    else:
                        vf_parts.append(
                            f"crop={crop_info['crop_w']}:{crop_info['crop_h']}:{crop_info['crop_x']}:{crop_info['crop_y']}"
                        )
            vf_parts.append("scale=1920:1080:force_original_aspect_ratio=decrease")
            vf_parts.append("pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black")

        vf_parts.append("setsar=1")
        vf_parts.append(f"fps={settings.shorts_fps}")

        vf_filter = ",".join(vf_parts)
        cmd = [
            settings.ffmpeg_binary,
            '-hide_banner', '-loglevel', 'error', '-nostdin',
            "-y",
            "-ss",
            f"{start_sec:.3f}",
            "-t",
            f"{dur_sec:.3f}",
            "-i",
            source_path,
            '-filter_complex' if layout_filter else '-vf',
            layout_filter or vf_filter,
            '-filter_complex_threads', '1',
            *(['-map', '[v]'] if layout_filter else []),
            "-an",
            '-pix_fmt', 'yuv420p',
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-threads",
            "2",
            "-crf",
            "23",
            str(out_segment_path),
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return out_segment_path.exists() and out_segment_path.stat().st_size > 1000
        except Exception as exc:
            logger.warning("Failed to cut scene segment %s: %s", out_segment_path, self._ffmpeg_error(getattr(exc, 'stderr', b'')) or str(exc))
            return False

    def _concat_segments(self, segment_paths: List[Path], out_concatenated_path: Path) -> bool:
        """Concatenate normalized video segments using FFmpeg concat demuxer."""
        if not segment_paths:
            return False
        sizes = {self._probe_video_dimensions(str(path)) for path in segment_paths}
        if len(sizes) != 1:
            raise ValueError('Scene sizes differ. Normalize every clip to the same 9:16 canvas before joining.')
        if len(segment_paths) == 1:
            import shutil
            shutil.copyfile(segment_paths[0], out_concatenated_path)
            return True

        concat_list_file = out_concatenated_path.parent / "concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for seg in segment_paths:
                f.write(f"file '{seg.resolve().as_posix()}'\n")

        cmd = [
            settings.ffmpeg_binary,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_list_file),
            "-c",
            "copy",
            str(out_concatenated_path),
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            return out_concatenated_path.exists() and out_concatenated_path.stat().st_size > 1000
        except Exception as exc:
            logger.warning("Concat demuxer failed: %s", exc)
            return False

    def build_shorts_filter_graph(
        self,
        crop_info: Dict[str, Any],
        shorts_width: int = 1080,
        shorts_height: int = 1920,
        foreground_width: int = 1220,
        foreground_zoom: float = 1.70,
        background_blur: int = 24,
        background_darkness: float = -0.08,
        foreground_brightness: float = 0.06,
        foreground_contrast: float = 1.08,
        foreground_saturation: float = 1.08,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Builds the same cinematic layout as the original movie-review renderer:
        - If the input video is already 9:16 vertical (e.g. motion teaser or user short), pass directly with light scaling.
        - Widescreen footage uses a full-frame blurred background and a centered,
          zoomed foreground. The canvas clips overscan; it must not cap zoom width.
        """
        orig_w = crop_info.get("original_width") or 1920
        orig_h = crop_info.get("original_height") or 1080

        # If already vertical or nearly square, pass through directly to avoid massive memory allocation
        if orig_w <= orig_h or (orig_w / max(orig_h, 1)) < 1.0:
            filter_parts = [
                f"[0:v]fps={settings.shorts_fps},scale={shorts_width}:{shorts_height}:force_original_aspect_ratio=increase,crop={shorts_width}:{shorts_height},format=yuv420p,setsar=1[v]"
            ]
            layout_details = {
                "canvas_width": shorts_width,
                "canvas_height": shorts_height,
                "effective_width": shorts_width,
                "foreground_height": shorts_height,
                "is_vertical_direct": True,
                "crop_info": crop_info,
            }
            return ";".join(filter_parts), layout_details

        source_chain = f"[0:v]fps={settings.shorts_fps},format=yuv420p"
        if crop_info.get("crop_applied"):
            if crop_info.get("crop_method") == "fallback":
                source_chain += ",crop=in_w:in_h*0.74:0:in_h*0.13"
            else:
                source_chain += (
                    f",crop={crop_info['crop_w']}:{crop_info['crop_h']}:{crop_info['crop_x']}:{crop_info['crop_y']}"
                )
        source_chain += ",split=2[bgsrc][fgsrc]"

        # Width is before canvas clipping: 1220 * 1.70 = 2074px, just like the
        # original renderer. Capping it to 1080 made every zoom setting look alike.
        effective_width = max(2, int(foreground_width * foreground_zoom) // 2 * 2)
        crop_w = crop_info.get("crop_w") or 1920
        crop_h = crop_info.get("crop_h") or 1080
        foreground_height = max(2, round(effective_width * crop_h / crop_w / 2) * 2)

        # Negative offsets center any oversize foreground instead of top-aligning it.
        centered_y = round((shorts_height - foreground_height) / 2)

        applied_blur = max(0, int(background_blur))

        filter_parts = [
            source_chain,
            (
                f"[bgsrc]scale={shorts_width}:{shorts_height}:force_original_aspect_ratio=increase,"
                f"crop={shorts_width}:{shorts_height},"
                f"boxblur={applied_blur}:1,"
                f"eq=brightness={background_darkness}:contrast=1.0:saturation=1.0[bg]"
            ),
            (
                f"[fgsrc]eq=brightness={foreground_brightness}:contrast={foreground_contrast}:saturation={foreground_saturation},"
                f"scale={effective_width}:-2[fg]"
            ),
            f"[bg][fg]overlay=(W-w)/2:{centered_y},format=yuv420p,setsar=1[v]",
        ]

        layout_details = {
            "canvas_width": shorts_width,
            "canvas_height": shorts_height,
            "effective_width": effective_width,
            "foreground_height": foreground_height,
            "overlay_x": "(W-w)/2",
            "overlay_y": centered_y,
            "foreground_zoom": foreground_zoom,
            "background_blur": applied_blur,
            "crop_info": crop_info,
        }

        return ";".join(filter_parts), layout_details

    def compose_shorts_video(
        self,
        project_id: int,
        source_video_paths: List[str],
        voice_audio_path: str,
        scenes: Optional[List[Dict[str, Any]]] = None,
        crop_black_bars: bool = True,
        foreground_zoom: Optional[float] = None,
        foreground_width: Optional[int] = None,
        output_filename: Optional[str] = None,
        include_bgm: bool = True,
        bgm_style: str = "suspense",
        bgm_volume: float = 0.35,
        bgm_ducking: bool = True,
        bgm_project: Optional[Dict[str, Any]] = None,
        thumbnail_path: Optional[str] = None,
        captions_path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compose 9:16 vertical shorts video with:
        - Black letterbox area cut (cropdetect or fallback)
        - Ambient background blur & foreground light grading
        - Voiceover audio sync
        - Royalty-free cinematic BGM auto-mixing
        - Ultra-low memory usage tailored for 512MB RAM cloud environments
        """
        if not source_video_paths:
            raise ValueError("At least one source video clip is required to render.")
        if not Path(voice_audio_path).exists():
            raise ValueError(f"Voice audio path not found: {voice_audio_path}")
        if thumbnail_path and not Path(thumbnail_path).is_file():
            raise ValueError("Thumbnail file missing. Generate/upload the thumbnail before composing.")

        out_name = output_filename or f"shorts_project_{project_id}.mp4"
        out_dir = settings.final_videos_dir / f"project_{project_id}"
        out_dir.mkdir(parents=True, exist_ok=True)
        final_video_path = out_dir / out_name
        render_video_path = out_dir / f'.render_{uuid4().hex}.mp4'

        segments_dir = out_dir / "segments"
        segments_dir.mkdir(parents=True, exist_ok=True)

        input_video_to_compose = source_video_paths[0]
        scene_layouts = {}

        # 1. Process Gemini scenes if available
        if scenes and len(scenes) > 0:
            logger.info("Composing video using %d Gemini scenes for project %s", len(scenes), project_id)
            valid_segment_paths: List[Path] = []
            for idx, sc in enumerate(scenes):
                src = sc.get("source_video_path")
                if not src and len(source_video_paths) == 1:
                    src = source_video_paths[0]
                allowed_sources = {str(Path(p).resolve()).casefold() for p in source_video_paths}
                if not src or str(Path(src).resolve()).casefold() not in allowed_sources or not os.path.isfile(src):
                    raise ValueError(f"Scene {idx + 1} has no valid source trailer. Re-select scenes or choose its source trailer.")

                st = float(sc.get("start_seconds", 0.0))
                dur = float(sc.get("duration_seconds", 3.5))
                seg_file = segments_dir / f"scene_{idx:02d}.mp4"

                scene_zoom = sc.get('cinematic_zoom', foreground_zoom)
                if scene_zoom is not None and not 1.0 <= float(scene_zoom) <= 2.0:
                    raise ValueError('Scene zoom must be between 1 and 2.')
                layout_key = src if 'cinematic_zoom' not in sc else f'{src} [zoom={scene_zoom}]'
                if layout_key not in scene_layouts:
                    scene_layouts[layout_key] = self._layout_for_source(src, crop_black_bars, scene_zoom, foreground_width)

                # Cut clip
                scene_filter = scene_layouts[layout_key][0]
                speed = float(sc.get('playback_speed', 1.0))
                if not .5 <= speed <= 1.0:
                    raise ValueError('Scene playback speed must be between 0.5 and 1.')
                effects = []
                if speed != 1:
                    effects.extend([f'trim=duration={dur * speed:.9f}', f'setpts=(PTS-STARTPTS)/{speed}',
                                    f'fps={settings.shorts_fps}', 'tpad=stop_mode=clone:stop_duration=0.1', f'trim=duration={dur:.9f}'])
                if sc.get('cinematic_grade'):
                    effects.extend(['eq=contrast=1.03:saturation=1.04', 'vignette=angle=PI/8'])
                if sc.get('cinematic_fade_in'):
                    effects.append('fade=t=in:st=0:d=0.12')
                if sc.get('cinematic_fade_out'):
                    effects.append(f'fade=t=out:st={max(0, dur-.12):.9f}:d=0.12')
                if effects:
                    scene_filter = scene_filter.replace('[v]', '[treated]') + ';[treated]' + ','.join(effects) + '[v]'
                if sc.get('cinematic_motion') == 'push_in':
                    scene_filter = scene_filter.replace('[v]', '[framed]') + (
                        f";[framed]zoompan=z='min(1.04,1+on*0.0004)':x='iw/2-iw/zoom/2':"
                        f"y='ih/2-ih/zoom/2':d=1:s={settings.shorts_width}x{settings.shorts_height}:"
                        f"fps={settings.shorts_fps},setsar=1[v]")
                if self._cut_scene_segment(src, st, dur, seg_file, crop_black_bars=False,
                                           layout_filter=scene_filter):
                    valid_segment_paths.append(seg_file)
                else:
                    raise ValueError(f"Scene {idx + 1} could not be cut from its selected trailer. Check its timings.")

            if valid_segment_paths:
                concatenated_scenes_path = out_dir / "concatenated_scenes.mp4"
                if not self._concat_segments(valid_segment_paths, concatenated_scenes_path):
                    raise RuntimeError("Could not join the selected scene timeline. Full trailers were not substituted.")
                input_video_to_compose = str(concatenated_scenes_path)

        # Fallback: if scenes were not cut and multiple source videos exist, concatenate them
        if input_video_to_compose == source_video_paths[0] and len(source_video_paths) > 1:
            multi_source_concat = out_dir / "all_sources_concat.mp4"
            valid_sources = [Path(p) for p in source_video_paths if os.path.exists(p)]
            if len(valid_sources) > 1 and self._concat_segments(valid_sources, multi_source_concat):
                input_video_to_compose = str(multi_source_concat)

        # 2. Detect black bars on the composed input video
        if scene_layouts:
            # Each clip already has its own crop/blur/zoom. The joined timeline
            # has a fixed vertical canvas and must not be cropped a second time.
            crop_info = {'original_width': settings.shorts_width, 'original_height': settings.shorts_height,
                'crop_w': settings.shorts_width, 'crop_h': settings.shorts_height,
                'crop_applied': False, 'crop_method': 'normalized_scenes', 'crop_x': 0, 'crop_y': 0}
        elif crop_black_bars:
            crop_info = self.detect_crop_area(input_video_to_compose)
        else:
            width, height = self._probe_video_dimensions(input_video_to_compose)
            crop_info = {'original_width': width, 'original_height': height, 'crop_w': width, 'crop_h': height,
                'crop_applied': False, 'crop_method': 'none', 'crop_x': 0, 'crop_y': 0}

        # Determine applied width and zoom
        if foreground_width is not None:
            applied_fg_width = foreground_width
        else:
            applied_fg_width = (
                settings.shorts_foreground_width_with_crop
                if crop_info.get("crop_applied")
                else settings.shorts_foreground_width_no_crop
            )

        if foreground_zoom is not None:
            applied_zoom = foreground_zoom
        else:
            applied_zoom = (
                settings.shorts_foreground_zoom_with_crop
                if crop_info.get("crop_applied")
                else settings.shorts_foreground_zoom_base
            )

        # 3. Build filter graph
        filter_complex, layout_details = self.build_shorts_filter_graph(
            crop_info=crop_info,
            shorts_width=settings.shorts_width,
            shorts_height=settings.shorts_height,
            foreground_width=applied_fg_width,
            foreground_zoom=applied_zoom,
            background_blur=settings.shorts_background_blur,
            background_darkness=settings.shorts_background_darkness,
            foreground_brightness=settings.shorts_foreground_brightness,
            foreground_contrast=settings.shorts_foreground_contrast,
            foreground_saturation=settings.shorts_foreground_saturation,
        )
        if scene_layouts:
            layout_details['scene_layouts'] = {source: details for source, (_, details) in scene_layouts.items()}

        # 4. Background Music (BGM) Track acquisition
        bgm_path = None
        bgm_info = None
        if include_bgm and bgm_style.lower() != "none":
            bgm_info = bgm_service.track_info(bgm_style, bgm_project)
            bgm_path = bgm_info['path']

        cmd = [
            settings.ffmpeg_binary,
            '-hide_banner', '-loglevel', 'error', '-nostdin',
            "-y",
            "-stream_loop",
            "-1",  # Loop video sequence seamlessly to match full voiceover
            "-i",
            str(input_video_to_compose),
            "-i",
            voice_audio_path,
        ]

        # If BGM is available, add as 3rd input and mix with voiceover
        if bgm_path and os.path.exists(bgm_path):
            cmd.extend([
                "-stream_loop",
                "-1",
                "-i",
                str(bgm_path),
            ])
            # Keep narration at unity; use the project's saved BGM gain and ducking.
            # amix with duration=first keeps exact length of voiceover
            audio_filter = bgm_service.mix_filter(self._probe_video_duration(voice_audio_path), bgm_volume, bgm_ducking)
            full_filter_complex = f"{filter_complex};{audio_filter}"
            audio_map_target = "[aout]"
        else:
            full_filter_complex = filter_complex
            audio_map_target = "1:a"

        video_map_target = "[v]"
        if captions_path:
            # FFmpeg filter syntax needs escaped Windows drive colons and quotes.
            subtitle_file = Path(captions_path).resolve().as_posix().replace(':', r'\:').replace("'", r"'\''")
            full_filter_complex = full_filter_complex.replace('[v]', '[uncaptioned]')
            full_filter_complex += f";[uncaptioned]subtitles=filename='{subtitle_file}'[v]"
        end_card = None
        if thumbnail_path:
            content_duration = self._probe_video_duration(voice_audio_path)
            total_duration = content_duration + 2.0
            image_index = 3 if bgm_path else 2
            cmd.extend(["-loop", "1", "-framerate", str(settings.shorts_fps), "-i", thumbnail_path])
            full_filter_complex += ";" + self._end_card_filter(image_index, content_duration,
                settings.shorts_width, settings.shorts_height, settings.shorts_fps)
            label = audio_map_target.strip('[]')
            full_filter_complex += f";[{label}]apad=pad_dur=2,atrim=duration={total_duration:.6f}[afinal]"
            video_map_target, audio_map_target = "[vfinal]", "[afinal]"
            cmd.extend(["-t", f"{total_duration:.6f}"])
            end_card = {"path": thumbnail_path, "duration_seconds": 2.0, "starts_at_seconds": content_duration}

        cmd.extend([
            "-filter_complex",
            full_filter_complex,
            "-filter_complex_threads",
            "1",
            "-map",
            video_map_target,
            "-map",
            audio_map_target,
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-threads",
            "2",
            "-max_muxing_queue_size",
            "512",
            "-crf",
            "23",
            "-c:a",
            "aac",
            "-b:a",
            "128k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(render_video_path),
        ])

        try:
            logger.info("Executing FFmpeg composition with crop & zoom: %s", " ".join(cmd))
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
            render_video_path.replace(final_video_path)
            return {
                "success": True,
                "project_id": project_id,
                "output_video_path": str(final_video_path).replace("\\", "/"),
                "crop_info": crop_info,
                "layout": layout_details,
                "bgm_mixed": bool(bgm_path and os.path.exists(bgm_path)),
                "bgm_style": bgm_style if bgm_path else None,
                "thumbnail_end_card": end_card,
                "bgm": {**({k: v for k, v in bgm_info.items() if k != 'path'} if bgm_info else {}),
                        "attribution": bgm_info.get('attribution', '') if bgm_info else '',
                        "enabled": bool(bgm_path), "style": bgm_style, "volume": bgm_volume, "ducking": bgm_ducking,
                        "mix_profile": "audible_v2"},
            }
        except subprocess.CalledProcessError as exc:
            err_msg = exc.stderr.decode("utf-8", errors="replace")
            (out_dir / 'render_error.log').write_text(err_msg, encoding='utf-8')
            logger.error("FFmpeg render failed: %s", err_msg)
            raise RuntimeError(f"FFmpeg render failed: {self._ffmpeg_error(exc.stderr)}") from exc
        finally:
            render_video_path.unlink(missing_ok=True)


video_composer_service = VideoComposerService()
