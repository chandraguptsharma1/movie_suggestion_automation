import json
import logging
from typing import Any, Dict, List
from app.config import settings
from app.services.tmdb_service import tmdb_service

logger = logging.getLogger(__name__)

try:
    from google import genai
except ImportError:
    genai = None

PRESET_CATEGORIES = [
    {
        "id": "mind_bending_thrillers",
        "title": "Top Mind-Bending & Psychological Thrillers",
        "description": "Mind games, crazy twists, and suspense that keeps you guessing till the final minute.",
        "icon": "🧠",
        "color": "from-red-500 to-rose-700",
        "default_query": "Psychological thriller mind bending",
    },
    {
        "id": "time_travel_scifi",
        "title": "Top Mind-Blowing Sci-Fi & Time Loops",
        "description": "Paradoxes, parallel universes, and high-concept time travel adventures.",
        "icon": "🚀",
        "color": "from-purple-500 to-indigo-700",
        "default_query": "Sci-Fi time loop time travel",
    },
    {
        "id": "survival_movies",
        "title": "Top Edge-of-the-Seat Survival Thrillers",
        "description": "Fight for life against ruthless wilderness, predators, deserted islands, or the abyss.",
        "icon": "🏝️",
        "color": "from-amber-500 to-orange-700",
        "default_query": "Survival thriller isolated",
    },
    {
        "id": "dark_horror",
        "title": "Top Truly Terrifying Psychological Horror",
        "description": "Atmospheric dread and bone-chilling terror without cheap jump scares.",
        "icon": "👻",
        "color": "from-slate-700 to-black",
        "default_query": "Psychological horror supernatural",
    },
    {
        "id": "netflix_underrated",
        "title": "Top Underrated OTT Hidden Gems",
        "description": "Must-watch masterpieces that 90% of viewers missed.",
        "icon": "💎",
        "color": "from-red-600 to-rose-900",
        "default_query": "Underrated thriller hidden gem",
    },
    {
        "id": "crime_heist",
        "title": "Top Smart Heist & Crime Masterminds",
        "description": "Brilliant plans, cat-and-mouse chases, and unpredictable double-crosses.",
        "icon": "💰",
        "color": "from-emerald-500 to-teal-700",
        "default_query": "Heist crime mastermind",
    },
]


class SuggestionService:
    def __init__(self):
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model

    def get_categories(self) -> List[Dict[str, Any]]:
        return PRESET_CATEGORIES

    def suggest_movies(self, category: str, count: int = 3) -> List[Dict[str, Any]]:
        """Suggest movies for a category using Gemini AI and enrich with TMDB data."""
        if not self.api_key or genai is None:
            # Fallback to direct TMDB search if Gemini not available
            return self._fallback_tmdb_suggest(category, count)

        prompt = f"""You are an elite cinema curator. Recommend exactly {count} top-tier movies that perfectly match this category/theme:
Category: "{category}"

Requirements:
- Only recommend critically acclaimed, highly engaging movies.
- Mix well-known hits with standout hidden gems.
- Output ONLY valid JSON in this exact structure:
```json
[
  {{
    "title": "Exact Official Movie Title",
    "year": "Release Year (e.g. 2014)",
    "hook": "1 short punchy sentence explaining why it's a masterpiece"
  }}
]
```
"""
        try:
            client = genai.Client(api_key=self.api_key)
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
            text = ""
            for m in candidate_models:
                try:
                    response = client.models.generate_content(
                        model=m,
                        contents=prompt,
                    )
                    text = response.text or ""
                    if text:
                        break
                except Exception as model_err:
                    logger.warning("Gemini model %s failed in suggestion: %s", m, model_err)

            if not text:
                return self._fallback_tmdb_suggest(category, count)

            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()

            items = json.loads(text)
            enriched = []
            for item in items[:count]:
                title = item.get("title", "")
                tmdb_results = tmdb_service.search_multi(title, media_type="movie")
                if tmdb_results:
                    match = tmdb_results[0]
                    match["hook"] = item.get("hook", "")
                    trailers = tmdb_service.fetch_videos(match["tmdb_id"], "movie")
                    match["trailers"] = trailers
                    match["trailers_count"] = len(trailers)
                    enriched.append(match)
                else:
                    enriched.append({
                        "title": title,
                        "year": str(item.get("year", "")),
                        "hook": item.get("hook", ""),
                        "overview": "",
                        "poster_url": None,
                        "backdrop_url": None,
                        "vote_average": 8.0,
                        "media_type": "movie",
                        "trailers": [],
                        "trailers_count": 0,
                    })
            return enriched
        except Exception as exc:
            logger.warning("Gemini suggestion failed: %s, falling back to TMDB search", exc)
            return self._fallback_tmdb_suggest(category, count)

    def _fallback_tmdb_suggest(self, category: str, count: int = 3) -> List[Dict[str, Any]]:
        results = tmdb_service.search_multi(category, media_type="movie")
        selected = results[:count]
        for m in selected:
            if m.get("tmdb_id"):
                vids = tmdb_service.fetch_videos(m["tmdb_id"], "movie")
                m["trailers"] = vids
                m["trailers_count"] = len(vids)
        return selected


suggestion_service = SuggestionService()
