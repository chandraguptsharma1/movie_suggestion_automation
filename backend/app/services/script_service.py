import json
import logging
import re
from typing import Any, Dict, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

try:
    from google import genai
except ImportError:
    genai = None


class ScriptService:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model
        models = [
            self.model,
            "gemini-3.5-flash",
            "gemini-3.5-flash-lite",
            "gemini-3.1-flash-lite",
            "gemini-3.1-flash-lite-preview",
            "gemini-2.5-flash",
        ]
        seen = set()
        self.candidate_models = [m for m in models if m and not (m in seen or seen.add(m))]

    def _call_gemini(self, prompt: str) -> str:
        if not self.api_key or genai is None:
            raise ValueError("GEMINI_API_KEY is required to generate script.")

        client = genai.Client(api_key=self.api_key)
        last_err = None
        for m in self.candidate_models:
            try:
                response = client.models.generate_content(
                    model=m,
                    contents=prompt,
                )
                if response and response.text:
                    return response.text
            except Exception as e:
                logger.warning("Gemini model %s failed: %s", m, e)
                last_err = e
        raise RuntimeError(f"All Gemini models failed: {last_err}")

    def generate_shorts_script(
        self,
        project_title: str,
        movies: List[Dict[str, Any]],
        audience_reviews: Optional[Dict[str, Any]] = None,
        creator_notes: str = "",
    ) -> Dict[str, Any]:
        count = len(movies)
        movie_descriptions = []
        insights = []

        for i, m in enumerate(movies, start=1):
            title = m.get("title") or f"Movie {i}"
            year = m.get("year") or ""
            overview = str(m.get("overview") or "")[:250]
            movie_descriptions.append(f"Movie #{i}: '{title}' ({year})\n   Story Premise: {overview}")

            t_id = str(m.get("tmdb_id") or title)
            revs = (audience_reviews or {}).get(t_id) or []
            if revs:
                snippets = [re.sub(r"[\"']", "", r.get("snippet", ""))[:120] for r in revs[:2]]
                insights.append(f"- '{title}': Praise: {' | '.join(snippets)}")
            else:
                insights.append(f"- '{title}': Known for extreme tension, incredible plot twists, and high suspense.")

        movie_count_str = f"the movie '{movies[0].get('title')}'" if count == 1 else f"{count} movies"
        spotlight_timing_str = (
            "- Movie Spotlight: 1 movie, detailed ~45-50s deep-dive with gripping plot build-up and climax excitement."
            if count == 1
            else f"- Movie Spotlights: {count} movies, perfectly proportioned for total 50-60s."
        )

        prompt = f"""You are the expert viral YouTube Shorts movie reviewer and scriptwriter for Reely Bee.
Your job is to write a high-retention 50 to 60 SECOND YouTube Shorts script in Devanagari Hindi (देवनागरी हिंदी लिपि) for {movie_count_str}.

CRITICAL REQUIREMENT FOR VOICE GENERATION (SARVAM AI TTS):
Sarvam AI's neural TTS engine (Bulbul model) is natively trained on Devanagari script.
To guarantee 100% accurate, natural, and glitch-free Indian pronunciation without robotic stuttering:
- The spoken script (full_script, hook, movie_spotlights, outro) MUST be generated in pure Devanagari Hindi (देवनागरी हिंदी).
- DO NOT write English or Hinglish in Latin script inside the spoken script.
- Common cinematic terms MUST be written phonetically in Devanagari:
  * "माइंड-ब्लोइंग" (not mind-blowing)
  * "क्लाइमेक्स" (not climax)
  * "सस्पेंस थ्रिलर" (not suspense thriller)
  * "ट्विस्ट" / "ट्विस्ट्स" (not twist)
  * "साइकोलॉजिकल" (not psychological)
  * "सुपरनैचुरल" (not supernatural)
  * "हॉरर" (not horror)
  * "खतरनाक" (not dangerous)
  * "ट्रस्ट मी" (not trust me)
  * "दिमाग हिला देने वाला" (not mind-bending)
  * "मूवी" / "फिल्म" (not movie/film)

Target Project: "{project_title}"
Total Movies: {count}
{f"Creator Notes: {creator_notes}" if creator_notes else ""}

### Movie Lineup:
{chr(10).join(movie_descriptions)}

### Internal Insights (What is Best in Each Movie - FOR YOUR CONTEXT ONLY):
{chr(10).join(insights)}

### STRICT STYLE & CONTENT RULES:
1. LANGUAGE & SCRIPT (DEVANAGARI HINDI ONLY):
   - Spoken text (full_script, hook, movie spotlights, outro) MUST be in conversational Devanagari Hindi (हिंदी लिपि).
   - Conversational, high-energy spoken tone (जैसे एक दोस्त दूसरे दोस्त को फुल एक्साइटमेंट और जोश में बता रहा हो).
   - Natural spoken transitions: "सोचो अगर...", "और भाई...", "लेकिन असली ट्विस्ट यह है...", "पर असली खेल तब शुरू होता है जब...".

2. STRUCTURE FOR EVERY MOVIE (STORY + DEKHNE KI WAJAH):
   Har movie ke spotlight me do cheezein clearly honi chahiye:
   a) MOVIE KI STORY: Film ka core concept, plot premise, danger ya mystery fast and gripping style me explain karein (NO spoilers).
   b) MOVIE DEKHNE KI WAJAH: Film dekhne ki solid wajah (jaise mind-blowing twist, edge-of-the-seat suspense, crazy climax).

3. ABSOLUTELY NO OTT / PLATFORM MENTIONS:
   - Kisi bhi OTT platform (Netflix, Prime Video, Hotstar, JioCinema, OTT) ka naam BILKUL NA LEIN.

4. ABSOLUTELY NO "LOG KYA KEH RAHE HAIN" / AUDIENCE QUOTES:
   - Script me ye BILKUL NAHI BOLNA hai ki "Log keh rahe hain...", "Public reaction hai...". Script me personal confident voice me baat karein.

5. STRICT TIMING (50 to 60 SECONDS / ~120-140 HINDI WORDS TOTAL):
   - Opening Hook (3-5 seconds / 15-20 words in Hindi).
   {spotlight_timing_str}
   - Outro (3-5 seconds / 10-15 words in Hindi call to action).

### Output JSON Format:
Respond STRICTLY with valid JSON (inside ```json ... ```):
{{
  "hook": "Opening 3-5s viral hook in Devanagari Hindi",
  "movie_spotlights": [
    {{
      "slot": 1,
      "title": "Movie Title",
      "duration_sec": 18,
      "story_premise": "Short story premise in Devanagari Hindi",
      "why_to_watch": "Reason to watch in Devanagari Hindi",
      "script_lines": "Combined spoken lines in Devanagari Hindi"
    }}
  ],
  "outro": "Closing 3-5s call to action in Devanagari Hindi",
  "full_script": "Full combined spoken script in Devanagari Hindi (Hook + Movie Spotlights + Outro) formatted for Sarvam AI voiceover",
  "hinglish_script": "Optional Romanized Hinglish script for creator reference",
  "youtube_title": "Punchy YouTube Shorts Title with #Shorts (under 70 chars)",
  "youtube_description": "Short description for YouTube with movie list and hashtags",
  "tags": ["Movie Review", "Hollywood Movies in Hindi", "Top Movies", "Shorts"],
  "hashtags": ["#Shorts", "#MovieReview", "#BestMovies"],
  "thumbnail_text": "3-5 word bold English hook for thumbnail (STRICTLY IN ENGLISH, e.g. 'SUPER ADDICTIVE MASTERPIECES')",
  "bgm_style": "Fast Dark Synthwave / Suspense Pulse"
}}
"""
        response_text = self._call_gemini(prompt)
        cleaned = response_text
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1].split("```")[0].strip()
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1].split("```")[0].strip()

        try:
            data = json.loads(cleaned)
        except Exception:
            data = {
                "hook": "",
                "movie_spotlights": [],
                "outro": "",
                "full_script": response_text.strip(),
                "youtube_title": f"{project_title} #Shorts",
                "youtube_description": "Watch these top movies! #Shorts",
                "tags": ["Shorts", "Movie Review"],
                "hashtags": ["#Shorts"],
                "thumbnail_text": "TOP MOVIES",
                "bgm_style": "Dramatic Suspense",
            }

        return data


script_service = ScriptService()
