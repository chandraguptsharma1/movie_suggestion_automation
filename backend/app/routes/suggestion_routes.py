from typing import Any, Dict, List, Literal
from fastapi import APIRouter, HTTPException, Query
from app.models.schemas import SuggestMoviesRequest
from app.services.suggestion_service import suggestion_service
from app.services.tmdb_service import tmdb_service, GENRE_MAP

router = APIRouter(prefix="/suggestions", tags=["Suggestions"])


@router.get('/movie-genres')
def movie_genres():
    return [{'id': key, 'name': value} for key, value in sorted(GENRE_MAP.items(), key=lambda item: item[1])]


@router.get('/discover')
def discover_movies(query: str = Query(default='', max_length=100),
                    year: int | None = Query(default=None, ge=1870, le=2100),
                    genre_id: int | None = Query(default=None, ge=1),
                    sort_by: Literal['popularity.desc', 'vote_average.desc', 'primary_release_date.desc'] = 'popularity.desc',
                    page: int = Query(default=1, ge=1, le=500)):
    try:
        return tmdb_service.browse_movies(query, year, genre_id, sort_by, page)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/categories")
def get_preset_categories() -> List[Dict[str, Any]]:
    return suggestion_service.get_categories()


@router.post("/suggest")
def suggest_movies(payload: SuggestMoviesRequest) -> List[Dict[str, Any]]:
    if not payload.category.strip():
        raise HTTPException(status_code=400, detail="Category name cannot be empty.")
    try:
        return suggestion_service.suggest_movies(payload.category.strip(), count=payload.count or 3)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/search")
def search_tmdb(query: str = Query(...), media_type: str = Query(default="movie")) -> List[Dict[str, Any]]:
    return tmdb_service.search_multi(query=query, media_type=media_type)
