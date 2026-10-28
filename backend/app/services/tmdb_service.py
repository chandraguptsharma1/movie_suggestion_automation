import logging
import json
import time
from uuid import uuid4
from typing import Any, Dict, List, Optional
import requests
from app.config import settings

logger = logging.getLogger(__name__)

TMDB_BASE_URL = "https://api.tmdb.org/3"
TMDB_IMAGE_BASE_URL = "https://image.tmdb.org/t/p"

GENRE_MAP = {
    28: "Action",
    12: "Adventure",
    16: "Animation",
    35: "Comedy",
    80: "Crime",
    99: "Documentary",
    18: "Drama",
    10751: "Family",
    14: "Fantasy",
    36: "History",
    27: "Horror",
    10402: "Music",
    9648: "Mystery",
    10749: "Romance",
    878: "Science Fiction",
    10770: "TV Movie",
    53: "Thriller",
    10752: "War",
    37: "Western",
}


class TMDBService:
    def __init__(self):
        self.bearer_token = settings.tmdb_bearer_token
        self.api_key = settings.tmdb_api_key

    def _headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        }
        if self.bearer_token:
            headers["Authorization"] = f"Bearer {self.bearer_token}"
        return headers

    def _params(self, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        params = extra or {}
        if not self.bearer_token and self.api_key:
            params["api_key"] = self.api_key
        return params

    def search_multi(self, query: str, media_type: str = "all", page: int = 1) -> List[Dict[str, Any]]:
        """Search movies and TV shows from TMDB."""
        if not query.strip():
            return []

        url = f"{TMDB_BASE_URL}/search/{'movie' if media_type == 'movie' else ('tv' if media_type == 'tv' else 'multi')}"
        params = self._params({"query": query, "page": page, "include_adult": False})
        try:
            resp = requests.get(url, headers=self._headers(), params=params, timeout=15)
            resp.raise_for_status()
            data = resp.json()
            results = data.get("results") or []
            return [self._format_tmdb_item(item) for item in results]
        except Exception as exc:
            logger.warning("TMDB search failed for '%s': %s", query, exc)
            return []

    def browse_movies(self, query='', year=None, genre_id=None, sort_by='popularity.desc', page=1):
        """Discover by year/genre, or search names with an honest pagination cursor."""
        query = query.strip()
        if genre_id is not None and genre_id not in GENRE_MAP:
            raise ValueError('Unknown movie category')
        results, cursor, total_pages, total_results = [], page, page, 0
        # Search has no with_genres parameter. Scan up to five search pages per
        # request when a genre is selected, preserving the next unscanned page.
        budget = 5 if query and genre_id is not None else 1
        try:
            for _ in range(budget):
                params = {'page': cursor, 'include_adult': False, 'language': 'en-US'}
                if query:
                    endpoint = 'search/movie'
                    params['query'] = query
                    if year:
                        params['primary_release_year'] = year
                else:
                    endpoint = 'discover/movie'
                    params.update(include_video=False, sort_by=sort_by)
                    if year:
                        params['primary_release_year'] = year
                    if genre_id is not None:
                        params['with_genres'] = genre_id
                    if sort_by == 'vote_average.desc':
                        params['vote_count.gte'] = 100
                for attempt in range(2):
                    try:
                        response = requests.get(f'{TMDB_BASE_URL}/{endpoint}', headers=self._headers(),
                            params=self._params(params), timeout=12)
                        if response.status_code in (429, 500, 502, 503, 504) and attempt == 0:
                            time.sleep(.4)
                            continue
                        break
                    except (requests.ConnectionError, requests.Timeout):
                        if attempt:
                            raise
                        time.sleep(.4)
                response.raise_for_status()
                data = response.json()
                total_pages = min(int(data.get('total_pages') or 0), 500)
                total_results = int(data.get('total_results') or 0)
                for item in data.get('results') or []:
                    if item.get('adult'):
                        continue
                    if query and genre_id is not None and genre_id not in (item.get('genre_ids') or []):
                        continue
                    results.append(self._format_tmdb_item(item))
                cursor += 1
                if cursor > total_pages or len(results) >= 20:
                    break
        except requests.HTTPError:
            raise RuntimeError(f'TMDB movie search returned HTTP {response.status_code}. Check TMDB access and retry.') from None
        except requests.RequestException as exc:
            raise RuntimeError(f'TMDB movie search unavailable ({type(exc).__name__}). Check connection and retry.') from None
        except (ValueError, TypeError, AttributeError):
            raise RuntimeError('TMDB returned an invalid movie search response. Please retry.') from None
        return {'results': results, 'next_page': cursor if cursor <= total_pages else None,
                'total_results': None if query and genre_id is not None else total_results,
                'sort': 'relevance' if query else sort_by}

    def fetch_videos(self, tmdb_id: int, media_type: str = "movie", *, strict: bool = False) -> List[Dict[str, Any]]:
        """Fetch trailer candidates; strict callers must distinguish API failure from no results."""
        if media_type not in ('movie', 'tv') or int(tmdb_id) <= 0:
            raise ValueError('Invalid TMDB movie/TV identifier')
        url = f"{TMDB_BASE_URL}/{media_type}/{tmdb_id}/videos"
        trailers = []
        seen = set()
        attempts, failures, complete_empty_response = 0, [], False
        # Retry an alternate language URL too: a failure on the English request
        # must not prevent Hindi or the unfiltered video collection from working.
        for language in ("en-US", "hi-IN", None):
            raw_videos = None
            for attempt in range(2):
                attempts += 1
                try:
                    params = {"language": language, "include_video_language": "en,hi,null"} if language else {}
                    resp = requests.get(
                        url, headers=self._headers(),
                        params=self._params(params), timeout=(5, 15),
                    )
                    if resp.status_code == 429 or resp.status_code >= 500:
                        if attempt == 0:
                            time.sleep(0.5 * (attempt + 1))
                            continue
                    resp.raise_for_status()
                    raw_videos = resp.json().get("results")
                    if not isinstance(raw_videos, list) or any(not isinstance(v, dict) for v in raw_videos):
                        raise ValueError('Invalid TMDB video list')
                    if language is None:
                        complete_empty_response = True
                    break
                except (requests.ConnectionError, requests.Timeout):
                    if attempt == 0:
                        time.sleep(.5)
                        continue
                    failures.append('connection')
                except requests.HTTPError:
                    error = f"TMDB videos request failed (HTTP {resp.status_code}). Check TMDB credentials/access."
                    if resp.status_code < 500 and resp.status_code != 429:
                        if strict:
                            raise RuntimeError(error) from None
                        return []
                    failures.append(f'HTTP {resp.status_code}')
                except (ValueError, AttributeError):
                    raw_videos = None
                    failures.append('invalid response')
                break

            for v in raw_videos or []:
                if (v.get("site") == "YouTube" and v.get("key") not in seen
                        and v.get("key") and v.get("type") in ("Trailer", "Teaser")):
                    seen.add(v["key"])
                    trailers.append({
                        "key": v["key"],
                        "youtube_id": v["key"],
                        "url": f"https://www.youtube.com/watch?v={v['key']}",
                        "name": v.get("name") or "Trailer",
                        "type": v.get("type") or "Trailer",
                        "official": bool(v.get("official")),
                    })
            if trailers:
                break
        trailers.sort(key=lambda x: (x["type"] != "Trailer", not x["official"]))
        if trailers:
            self._save_video_cache(tmdb_id, media_type, trailers)
        elif failures and not complete_empty_response:
            cached = self._load_video_cache(tmdb_id, media_type)
            if cached:
                logger.warning('TMDB unavailable for %s/%s; retrying verified trailer downloads using saved links.', media_type, tmdb_id)
                return cached
            error = (f'TMDB connection failed after {attempts} attempts across English, Hindi and default video requests.'
                     if 'connection' in failures else f'TMDB videos unavailable ({failures[-1]}).')
            error += ' No saved trailer links available. Retry or add an official trailer URL in Trailers & Clips.'
            if strict:
                raise RuntimeError(error) from None
            logger.warning('%s Media: %s/%s', error, media_type, tmdb_id)
        return trailers

    def _video_cache_path(self, tmdb_id, media_type):
        return settings.storage_path / 'tmdb_cache' / 'videos' / f'{media_type}_{int(tmdb_id)}.json'

    def _save_video_cache(self, tmdb_id, media_type, trailers):
        path = self._video_cache_path(tmdb_id, media_type)
        temp = path.with_name(f'{path.stem}_{uuid4().hex}.tmp')
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            temp.write_text(json.dumps({'tmdb_id': int(tmdb_id), 'media_type': media_type,
                'saved_at': time.time(), 'trailers': trailers}, ensure_ascii=False), encoding='utf-8')
            temp.replace(path)
        except OSError:
            logger.warning('Could not save TMDB trailer cache for %s/%s', media_type, tmdb_id)
        finally:
            temp.unlink(missing_ok=True)

    def _load_video_cache(self, tmdb_id, media_type):
        try:
            data = json.loads(self._video_cache_path(tmdb_id, media_type).read_text(encoding='utf-8'))
            if data.get('tmdb_id') != int(tmdb_id) or data.get('media_type') != media_type:
                return []
            if not 0 <= time.time() - float(data['saved_at']) <= 30 * 86400:
                return []
            trailers = data['trailers']
            if not isinstance(trailers, list) or any(not isinstance(item, dict) or not item.get('key')
                or item.get('url') != f"https://www.youtube.com/watch?v={item['key']}"
                or item.get('type') not in ('Trailer', 'Teaser') for item in trailers):
                return []
            return trailers
        except (OSError, ValueError, KeyError, TypeError):
            return []

    def fetch_reviews(self, tmdb_id: int, media_type: str = "movie") -> List[Dict[str, Any]]:
        """Fetch user reviews for a movie."""
        url = f"{TMDB_BASE_URL}/{media_type}/{tmdb_id}/reviews"
        try:
            resp = requests.get(url, headers=self._headers(), params=self._params(), timeout=15)
            resp.raise_for_status()
            data = resp.json()
            raw = data.get("results") or []
            reviews = []
            for r in raw[:3]:
                content = (r.get("content") or "").strip()
                reviews.append({
                    "author": r.get("author") or "Viewer",
                    "rating": (r.get("author_details") or {}).get("rating"),
                    "snippet": content[:240],
                })
            return reviews
        except Exception as exc:
            logger.warning("Failed fetching reviews for tmdb_id %s: %s", tmdb_id, exc)
            return []

    def _format_tmdb_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        title = item.get("title") or item.get("name") or ""
        media_type = item.get("media_type") or ("movie" if "title" in item else "tv")
        rel_date = item.get("release_date") or item.get("first_air_date") or ""
        year = rel_date[:4] if rel_date else ""
        poster_path = item.get("poster_path")
        backdrop_path = item.get("backdrop_path")
        poster_url = f"{TMDB_IMAGE_BASE_URL}/w500{poster_path}" if poster_path else None
        backdrop_url = f"{TMDB_IMAGE_BASE_URL}/original{backdrop_path}" if backdrop_path else None

        genre_ids = item.get("genre_ids") or []
        genres = [GENRE_MAP.get(gid) for gid in genre_ids if GENRE_MAP.get(gid)]

        return {
            "tmdb_id": item.get("id"),
            "title": title,
            "year": year,
            "overview": item.get("overview") or "",
            "poster_url": poster_url,
            "backdrop_url": backdrop_url,
            "vote_average": round(float(item.get("vote_average") or 0.0), 1),
            "media_type": media_type,
            "genres": genres,
            "platform": "OTT",
        }


tmdb_service = TMDBService()
