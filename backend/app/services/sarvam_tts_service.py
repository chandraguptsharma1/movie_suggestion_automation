import base64
import hashlib
import io
import logging
import os
import re
import subprocess
import wave
from pathlib import Path
import time
from typing import List, Optional, Dict
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry
from app.config import settings

logger = logging.getLogger(__name__)


class SarvamTTSService:
    provider = "sarvam"
    emotion_tag_pattern = re.compile(
        r"\[(Excited|Whisper|Scared|Hyped|Funny|Emotional|Suspense|Dark|Fast|Slow|Hook|Outro|Movie\s*\d+)\]",
        flags=re.IGNORECASE,
    )

    COMMON_PHONETIC_REPLACEMENTS: Dict[str, str] = {
        r"\bmind[- ]blowing\b": "माइंड-ब्लोइंग",
        r"\bclimax\b": "क्लाइमेक्स",
        r"\btwist\b": "ट्विस्ट",
        r"\btwists\b": "ट्विस्ट्स",
        r"\bsuspense\b": "सस्पेंस",
        r"\bthriller\b": "थ्रिलर",
        r"\bpsychological\b": "साइकोलॉजिकल",
        r"\bsupernatural\b": "सुपरनैचुरल",
        r"\bhorror\b": "हॉरर",
        r"\bmystery\b": "मिस्ट्री",
        r"\btrust me\b": "ट्रस्ट मी",
        r"\bmovie\b": "मूवी",
        r"\bmovies\b": "मूवीज",
        r"\bfilm\b": "फिल्म",
        r"\bfilms\b": "फिल्म्स",
        r"\bscene\b": "सीन",
        r"\bscenes\b": "सीन्स",
        r"\bcharacter\b": "कैरेक्टर",
        r"\bcharacters\b": "कैरेक्टर्स",
        r"\bsubscribe\b": "सब्सक्राइब",
        r"\bcomment\b": "कमेंट",
        r"\bnext level\b": "नेक्स्ट लेवल",
        r"\bmasterpiece\b": "मास्टरपीस",
    }

    SPEAKER_ALIASES = {
        "vipul": "vipul_hi_social",
        "vipul_hi_social": "vipul_hi_social",
        "sunny": "sunny_hi_reels",
        "sunny_hi_reels": "sunny_hi_reels",
        "shubh": "shubh_hi_stories_dramatic",
        "shubh_hi_stories_dramatic": "shubh_hi_stories_dramatic",
        "aditya": "aditya_hi_conversational",
        "aditya_hi_conversational": "aditya_hi_conversational",
        "kabir": "kabir_hi_conversational",
        "kabir_hi_conversational": "kabir_hi_conversational",
        "simran": "simran_hi_conversation",
        "simran_hi_conversation": "simran_hi_conversation",
        "ritu": "ritu_hi_reels",
        "ritu_hi_reels": "ritu_hi_reels",
    }

    def __init__(self):
        self.api_key = settings.sarvam_api_key
        self.model = settings.sarvam_model or "bulbul:v4-flash"
        self.speaker = settings.sarvam_speaker or "vipul_hi_social"
        self.endpoint = "https://api.sarvam.ai/text-to-speech"

    def clean_voice_text(self, text: str) -> str:
        """Removes director tags, normalizes common cinematic loanwords to Devanagari, and cleans whitespace."""
        cleaned = self.emotion_tag_pattern.sub("", text or "")
        cleaned = re.sub(r"\[.*?\]", "", cleaned)
        for pattern, replacement in self.COMMON_PHONETIC_REPLACEMENTS.items():
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
        cleaned = re.sub(r" *\n *", "\n", cleaned)
        return cleaned.strip()

    def chunk_text(self, text: str, max_chars: int = 420) -> List[str]:
        """
        Splits text into chunks under Sarvam's character limit, breaking at sentence boundaries.
        """
        cleaned = self.clean_voice_text(text)
        if not cleaned:
            return []
        if len(cleaned) <= max_chars:
            return [cleaned]

        sentences = re.split(r"(?<=[.!?।\n])\s+", cleaned)
        chunks: List[str] = []
        current_chunk = ""

        for s in sentences:
            s = s.strip()
            if not s:
                continue

            if len(s) > max_chars:
                words = s.split()
                for w in words:
                    if len(current_chunk) + len(w) + 1 <= max_chars:
                        current_chunk = f"{current_chunk} {w}".strip()
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = w
                continue

            if len(current_chunk) + len(s) + 1 <= max_chars:
                current_chunk = f"{current_chunk} {s}".strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = s

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def generate_audio(
        self,
        text: str,
        output_path: str,
        speaker: Optional[str] = None,
        pace: float = 1.05,
    ) -> dict:
        if not self.api_key:
            raise ValueError("SARVAM_API_KEY is not configured.")

        selected_speaker = self.SPEAKER_ALIASES.get((speaker or self.speaker).strip().lower(), self.speaker)
        chunks = self.chunk_text(text, max_chars=400)
        if not chunks:
            raise ValueError("No valid voice text found for TTS generation.")

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        audio_segments = []
        session = requests.Session()
        retries = Retry(
            total=3,
            connect=3,
            read=3,
            backoff_factor=1.2,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        session.mount("https://", HTTPAdapter(max_retries=retries))

        for i, chunk in enumerate(chunks):
            headers = {
                "api-subscription-key": self.api_key,
                "Content-Type": "application/json",
            }
            payload = {
                "inputs": [chunk],
                "target_language_code": "hi-IN",
                "speaker": selected_speaker,
                "pitch": 0,
                "pace": pace,
                "loudness": 1.5,
                "speech_sample_rate": 22050,
                "enable_preprocessing": True,
                "model": self.model,
            }

            chunk_success = False
            last_err = None

            for attempt in range(1, 4):
                try:
                    logger.info("Calling Sarvam TTS for chunk %d/%d (attempt %d)", i + 1, len(chunks), attempt)
                    resp = session.post(self.endpoint, json=payload, headers=headers, timeout=(10, 45))
                    if resp.status_code == 200:
                        data = resp.json()
                        audios = data.get("audios") or []
                        if audios:
                            wav_bytes = base64.b64decode(audios[0])
                            audio_segments.append(wav_bytes)
                            chunk_success = True
                            break
                        last_err = "No audio data returned by Sarvam"
                    else:
                        last_err = f"HTTP {resp.status_code}: {resp.text[:150]}"
                        logger.warning("Sarvam TTS chunk %d attempt %d error: %s", i + 1, attempt, last_err)
                except Exception as exc:
                    last_err = str(exc)
                    logger.warning("Sarvam TTS chunk %d attempt %d connection timeout/error: %s", i + 1, attempt, exc)

                if attempt < 3:
                    time.sleep(1.0 * attempt)

            if not chunk_success:
                raise RuntimeError(
                    f"Sarvam AI connection failed for chunk {i + 1} after 3 retries: {last_err}. "
                    "Please check your internet connection or try again in a few seconds."
                )

        # Merge WAV segments
        merged_wav_bytes = self._concat_wav_bytes(audio_segments)

        # Save to MP3 (or WAV if ffmpeg is not available)
        final_saved_path = self._save_or_convert_to_mp3(merged_wav_bytes, out_file)
        duration_sec = self._get_wav_duration(merged_wav_bytes)

        return {
            "success": True,
            "provider": "sarvam",
            "speaker": selected_speaker,
            "model": self.model,
            "pace": pace,
            "audio_path": str(final_saved_path).replace("\\", "/"),
            "duration_seconds": round(duration_sec, 2),
            "chunks_count": len(chunks),
        }

    def _concat_wav_bytes(self, segments: List[bytes]) -> bytes:
        if len(segments) == 1:
            return segments[0]

        buf_out = io.BytesIO()
        first = segments[0]
        with wave.open(io.BytesIO(first), "rb") as w_in:
            params = w_in.getparams()

        with wave.open(buf_out, "wb") as w_out:
            w_out.setparams(params)
            for seg in segments:
                with wave.open(io.BytesIO(seg), "rb") as w_part:
                    w_out.writeframes(w_part.readframes(w_part.getnframes()))

        return buf_out.getvalue()

    def _get_wav_duration(self, wav_bytes: bytes) -> float:
        try:
            with wave.open(io.BytesIO(wav_bytes), "rb") as w:
                return float(w.getnframes()) / float(w.getframerate())
        except Exception:
            return 0.0

    def _save_or_convert_to_mp3(self, wav_bytes: bytes, target_path: Path) -> Path:
        wav_path = target_path.with_suffix(".wav")
        with wav_path.open("wb") as f:
            f.write(wav_bytes)

        if target_path.suffix.lower() == ".mp3":
            try:
                cmd = [
                    settings.ffmpeg_binary,
                    "-y",
                    "-i",
                    str(wav_path),
                    "-codec:a",
                    "libmp3lame",
                    "-b:a",
                    "192k",
                    str(target_path),
                ]
                res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
                if wav_path.exists():
                    wav_path.unlink()
                return target_path
            except Exception as e:
                logger.warning("FFmpeg mp3 convert failed, keeping WAV: %s", e)
                return wav_path

        return wav_path


sarvam_tts_service = SarvamTTSService()
