import json
import logging
import os
import shutil
import subprocess
import urllib.request
import uuid
from pathlib import Path
from typing import Optional

from app.config import settings

logger = logging.getLogger(__name__)

BGM_ASSETS_DIR = Path(__file__).resolve().parent.parent.parent / "assets" / "bgm"
BGM_STORAGE_DIR = settings.storage_path / "bgm"
BGM_DIR = BGM_STORAGE_DIR
BGM_DIR.mkdir(parents=True, exist_ok=True)

# Curated library of 20 YouTube Audio Library tracks
RAW_TRACKS = [
    {
        "id": "ticking_beneath_the_steel",
        "title": "Ticking Beneath the Steel",
        "filename": "Ticking_Beneath_the_Steel.mp3",
        "label": "Ticking Suspense (Ticking Beneath the Steel)",
        "mood": "Suspense / Countdown Thriller",
    },
    {
        "id": "beneath_the_floorboards",
        "title": "Beneath The Floorboards",
        "filename": "Beneath_The_Floorboards.mp3",
        "label": "Dark Mystery (Beneath The Floorboards)",
        "mood": "Mystery / Detective",
    },
    {
        "id": "before_the_heavy_silence",
        "title": "Before The Heavy Silence",
        "filename": "Before_The_Heavy_Silence.mp3",
        "label": "Deep Atmospheric Tension (Before The Heavy Silence)",
        "mood": "Deep Tension / Ambient Horror",
    },
    {
        "id": "beneath_the_iron_sky",
        "title": "Beneath The Iron Sky",
        "filename": "Beneath_The_Iron_Sky.mp3",
        "label": "Dark Epic Cinematic (Beneath The Iron Sky)",
        "mood": "Epic Cinematic Drama",
    },
    {
        "id": "concrete_heartbeat",
        "title": "Concrete Heartbeat",
        "filename": "Concrete_Heartbeat.mp3",
        "label": "Modern Rhythmic Pulse (Concrete Heartbeat)",
        "mood": "Rhythmic Beat / Urban Suspense",
    },
    {
        "id": "midnight_on_the_pavement",
        "title": "Midnight on the Pavement",
        "filename": "Midnight_on_the_Pavement.mp3",
        "label": "Crime Noir (Midnight on the Pavement)",
        "mood": "Dark Noir / Night Mystery",
    },
    {
        "id": "the_midnight_inquiry",
        "title": "The Midnight Inquiry",
        "filename": "The_Midnight_Inquiry.mp3",
        "label": "Detective Investigation (The Midnight Inquiry)",
        "mood": "Investigation / Whodunit",
    },
    {
        "id": "the_omen_of_impact",
        "title": "The Omen of Impact",
        "filename": "The_Omen_of_Impact.mp3",
        "label": "Action Tension (The Omen of Impact)",
        "mood": "Action / High Stakes Tension",
    },
    {
        "id": "trenchcoat_shadow",
        "title": "Trenchcoat Shadow",
        "filename": "Trenchcoat_Shadow.mp3",
        "label": "Classic Detective Noir (Trenchcoat Shadow)",
        "mood": "Detective Noir Thriller",
    },
    {
        "id": "a_broken_alibi",
        "title": "A Broken Alibi",
        "filename": "A_Broken_Alibi.mp3",
        "label": "Suspense Whodunit (A Broken Alibi)",
        "mood": "Crime Investigation",
    },
    {
        "id": "orbits_over_water",
        "title": "Orbits Over Water",
        "filename": "Orbits_Over_Water.mp3",
        "label": "Ethereal Ambient (Orbits Over Water)",
        "mood": "Atmospheric Space & Mystery",
    },
    {
        "id": "beyond_the_ridge",
        "title": "Beyond the Ridge",
        "filename": "Beyond_the_Ridge.mp3",
        "label": "Adventure Drama (Beyond the Ridge)",
        "mood": "Adventure & Emotional Journey",
    },
    {
        "id": "the_heavy_weight_of_glass",
        "title": "The Heavy Weight of Glass",
        "filename": "The_Heavy_Weight_of_Glass.mp3",
        "label": "Dramatic Tension (The Heavy Weight of Glass)",
        "mood": "Intense Psychological Drama",
    },
    {
        "id": "winter_in_the_foundries",
        "title": "Winter in the Foundries",
        "filename": "Winter_in_the_Foundries.mp3",
        "label": "Industrial Suspense (Winter in the Foundries)",
        "mood": "Industrial & Cold Suspense",
    },
    {
        "id": "beyond_the_gilded_gates",
        "title": "Beyond the Gilded Gates",
        "filename": "Beyond_the_Gilded_Gates.mp3",
        "label": "Grand Mystery (Beyond the Gilded Gates)",
        "mood": "Grand Historical / Mystery",
    },
    {
        "id": "the_meridian_unfolds",
        "title": "The Meridian Unfolds",
        "filename": "The_Meridian_Unfolds.mp3",
        "label": "Cinematic Journey (The Meridian Unfolds)",
        "mood": "Epic Cinematic Odyssey",
    },
    {
        "id": "a_case_for_lunch",
        "title": "A Case for Lunch",
        "filename": "A_Case_for_Lunch.mp3",
        "label": "Light Mystery (A Case for Lunch)",
        "mood": "Light Quirky Mystery",
    },
    {
        "id": "sunday_morning_mischief",
        "title": "Sunday Morning Mischief",
        "filename": "Sunday_Morning_Mischief.mp3",
        "label": "Upbeat Mischief (Sunday Morning Mischief)",
        "mood": "Lighthearted & Playful",
    },
    {
        "id": "sidewalks_and_secret_songs",
        "title": "Sidewalks And Secret Songs",
        "filename": "Sidewalks_And_Secret_Songs.mp3",
        "label": "Emotional Drama (Sidewalks And Secret Songs)",
        "mood": "Emotional Storytelling",
    },
    {
        "id": "where_giants_roam",
        "title": "Where Giants Roam",
        "filename": "Where_Giants_Roam.mp3",
        "label": "Epic Fantasy (Where Giants Roam)",
        "mood": "Fantasy & Wonder Tension",
    },
]

# Primary category aliases mapped to top YouTube Audio Library tracks
BGM_CATALOG = {
    "suspense": {
        "filename": "Ticking_Beneath_the_Steel.mp3",
        "title": "Ticking Beneath the Steel",
        "label": "Ticking Suspense (Ticking Beneath the Steel)",
        "mood": "Suspense / Countdown Thriller",
        "license": "YouTube Audio Library (Royalty-free)",
    },
    "mystery": {
        "filename": "Beneath_The_Floorboards.mp3",
        "title": "Beneath The Floorboards",
        "label": "Dark Mystery (Beneath The Floorboards)",
        "mood": "Mystery / Detective",
        "license": "YouTube Audio Library (Royalty-free)",
    },
    "epic": {
        "filename": "Beneath_The_Iron_Sky.mp3",
        "title": "Beneath The Iron Sky",
        "label": "Dark Epic Cinematic (Beneath The Iron Sky)",
        "mood": "Epic Cinematic Drama",
        "license": "YouTube Audio Library (Royalty-free)",
    },
    "ambient": {
        "filename": "Before_The_Heavy_Silence.mp3",
        "title": "Before The Heavy Silence",
        "label": "Deep Atmospheric Tension (Before The Heavy Silence)",
        "mood": "Deep Tension / Ambient Horror",
        "license": "YouTube Audio Library (Royalty-free)",
    },
}

for item in RAW_TRACKS:
    entry = {
        "filename": item["filename"],
        "title": item["title"],
        "label": item["label"],
        "mood": item["mood"],
        "license": "YouTube Audio Library (Royalty-free)",
    }
    BGM_CATALOG[item["id"]] = entry
    stem = Path(item["filename"]).stem.lower()
    BGM_CATALOG[stem] = entry


class BGMService:
    """YouTube Audio Library tracks and project-local custom audio."""

    def __init__(self):
        self.bgm_dir = BGM_STORAGE_DIR

    def get_bgm_track(self, style: str = "suspense") -> Optional[str]:
        """
        Retrieves the local path for the requested BGM style.
        Looks in storage directory, then assets directory.
        """
        track_info = BGM_CATALOG.get(style.lower()) or BGM_CATALOG["suspense"]
        filename = track_info["filename"]

        # Check storage directory first
        out_path = self.bgm_dir / filename
        if out_path.exists() and self.is_audio(out_path):
            return str(out_path).replace("\\", "/")

        # Check assets directory
        asset_path = BGM_ASSETS_DIR / filename
        if asset_path.exists() and self.is_audio(asset_path):
            try:
                self.bgm_dir.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(asset_path, out_path)
                return str(out_path).replace("\\", "/")
            except Exception:
                return str(asset_path).replace("\\", "/")

        # Fallback URL if present
        url = track_info.get("url")
        if url:
            try:
                logger.info("Downloading fallback BGM track: %s...", track_info["label"])
                req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                temporary = out_path.with_name(f"{out_path.stem}_{uuid.uuid4().hex[:8]}.part")
                try:
                    with urllib.request.urlopen(req, timeout=30) as resp, temporary.open("wb") as file:
                        total = 0
                        while chunk := resp.read(1024 * 1024):
                            total += len(chunk)
                            if total > 30 * 1024 * 1024:
                                raise ValueError("Music file exceeds 30 MB.")
                            file.write(chunk)
                    if not self.is_audio(temporary):
                        raise ValueError("Downloaded music is not valid audio.")
                    temporary.replace(out_path)
                finally:
                    temporary.unlink(missing_ok=True)
                if out_path.exists():
                    logger.info("BGM cached successfully at: %s", out_path)
                    return str(out_path).replace("\\", "/")
            except Exception as exc:
                logger.warning("Could not download BGM from %s: %s", url, exc)

        return None

    @staticmethod
    def is_audio(path):
        try:
            result = subprocess.run(
                [
                    settings.ffprobe_binary,
                    "-v",
                    "error",
                    "-show_streams",
                    "-show_format",
                    "-of",
                    "json",
                    str(path),
                ],
                capture_output=True,
                text=True,
                check=True,
                timeout=15,
            )
            data = json.loads(result.stdout)
            return float(data.get("format", {}).get("duration") or 0) > 0 and any(
                s.get("codec_type") == "audio" for s in data.get("streams", [])
            )
        except (OSError, ValueError, subprocess.SubprocessError):
            return False

    def track_info(self, style, project=None):
        if style == "custom":
            saved = (project or {}).get("bgm_data_json") or {}
            path = Path(saved.get("custom_path") or "")
            expected = self.bgm_dir / f"project_{int((project or {}).get('id', 0))}"
            if (
                not path.is_file()
                or not path.resolve().is_relative_to(expected.resolve())
                or not self.is_audio(path)
            ):
                raise ValueError("Pehle apna valid music track upload karein.")
            return {
                "path": str(path),
                "style": style,
                "label": saved.get("custom_name") or "Uploaded music",
                "attribution": saved.get("custom_credit") or "",
                "license": "User-provided; verify usage rights",
            }
        if style.lower() not in BGM_CATALOG:
            raise ValueError(f"Unknown music style: '{style}'.")
        track = BGM_CATALOG[style.lower()]
        path = self.get_bgm_track(style)
        if not path:
            raise ValueError("Selected background music track not found.")
        title = track.get("title", style.replace("_", " ").title())
        credit = (
            f'Music: "{title}" via YouTube Audio Library\n'
            "Royalty-free music for creators."
        )
        return {
            "path": path,
            "style": style,
            "label": track["label"],
            "mood": track.get("mood", ""),
            "license": track.get("license", "YouTube Audio Library (Royalty-free)"),
            "source_url": track.get("url", ""),
            "attribution": credit,
        }

    @staticmethod
    def mix_filter(duration, volume=0.15, ducking=True):
        if not 0 <= volume <= 0.5 or duration <= 0:
            raise ValueError("Music volume must be 0–50%, and audio duration must be positive.")
        fade = min(1.5, duration / 2)
        music = (
            f"[2:a]atrim=duration={duration:.3f},asetpts=PTS-STARTPTS,"
            f"loudnorm=I=-16:TP=-2:LRA=7,aresample=48000,aformat=channel_layouts=stereo,"
            f"volume={volume:.4f},afade=t=in:d={min(0.6, duration / 2):.3f},"
            f"afade=t=out:st={duration-fade:.3f}:d={fade:.3f}[music]"
        )
        voice = "[1:a]aresample=48000,aformat=channel_layouts=stereo"
        if ducking:
            return (
                voice
                + ",asplit=2[voice][key];"
                + music
                + ";[music][key]sidechaincompress=threshold=0.14:ratio=2.4:attack=15:release=200[ducked];"
                + "[voice][ducked]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0:latency=1[aout]"
            )
        return (
            voice
            + "[voice];"
            + music
            + ";[voice][music]amix=inputs=2:duration=first:normalize=0,alimiter=limit=0.95:level=0:latency=1[aout]"
        )

    @staticmethod
    def credit_description(script_data, music, previous_music=None):
        data = dict(script_data or {})
        description = data.get("youtube_description") or ""
        previous = (previous_music or {}).get("attribution") or ""
        if previous:
            description = description.replace("\n\nMusic credit:\n" + previous, "").strip()
        credit = music.get("attribution") if music.get("enabled") else ""
        if credit:
            description += "\n\nMusic credit:\n" + credit
        data["youtube_description"] = description.strip()
        return data


bgm_service = BGMService()
