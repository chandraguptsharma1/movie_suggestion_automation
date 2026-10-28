import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from app.database import project_repo
from app.models.schemas import CreateProjectRequest, MovieItem
from app.services.tmdb_service import tmdb_service
from app.services.suggestion_service import suggestion_service
from app.services.auto_pilot_service import auto_pilot_service

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.post("")
def create_project(payload: CreateProjectRequest) -> Dict[str, Any]:
    enriched_movies = []
    all_trailers = []

    for idx, m in enumerate(payload.movies, start=1):
        m_dict = m.model_dump()
        m_dict["slot"] = idx
        trailers = m_dict.get("trailers") or []

        # If tmdb_id present and no trailers, auto-fetch
        if m_dict.get("tmdb_id") and not trailers:
            fetched_trailers = tmdb_service.fetch_videos(m_dict["tmdb_id"], m_dict.get("media_type") or "movie")
            for t in fetched_trailers:
                t["movie_title"] = m_dict["title"]
                t["movie_slot"] = idx
            trailers = fetched_trailers
            m_dict["trailers"] = trailers
            m_dict["trailers_count"] = len(trailers)

        all_trailers.extend(trailers)
        enriched_movies.append(m_dict)

    title = payload.title
    if not title or not title.strip():
        movie_titles_str = ", ".join(m["title"] for m in enriched_movies)
        if len(enriched_movies) == 1:
            title = f"Movie Spotlight: {movie_titles_str}"
        else:
            title = f"Top {len(enriched_movies)} Shorts: {movie_titles_str}"

    prefix = "SPOT" if len(enriched_movies) == 1 else "GROUP"
    job_code = f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

    project_data = {
        "job_code": job_code,
        "title": title.strip(),
        "notes": payload.notes or "",
        "movie_count": len(enriched_movies),
        "movies_json": enriched_movies,
        "trailers_json": all_trailers,
        "script_text": payload.script_text or "",
        "script_data_json": payload.script_data or {},
        "status": "SCRIPT_READY" if payload.script_text else "CREATED",
        "progress_percent": 75 if payload.script_text else 25,
    }

    created = project_repo.create(project_data)
    return created


@router.get("")
def list_projects(limit: int = Query(default=100, ge=1, le=100)) -> List[Dict[str, Any]]:
    return project_repo.list_all(limit=limit)


@router.get("/{project_id}")
def get_project(project_id: int) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.delete("/{project_id}")
def delete_project(project_id: int) -> Dict[str, Any]:
    success = project_repo.delete(project_id)
    if not success:
        raise HTTPException(status_code=404, detail="Project not found")
    return {"success": True, "message": "Project deleted successfully"}


@router.post("/{project_id}/reviews")
def fetch_audience_reviews(project_id: int) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    movies = project.get("movies_json") or []
    reviews_map = {}

    for m in movies:
        tmdb_id = m.get("tmdb_id")
        title = m.get("title") or "Movie"
        reviews = []
        if tmdb_id:
            reviews = tmdb_service.fetch_reviews(int(tmdb_id), m.get("media_type") or "movie")

        if not reviews:
            rating = m.get("vote_average") or 8.0
            reviews = [{
                "author": "Viewer Reaction",
                "rating": rating,
                "snippet": f"Praised for its unpredictable plot twists and edge-of-the-seat tension. Rated {rating}/10.",
            }]

        reviews_map[str(tmdb_id or title)] = reviews

    updated = project_repo.update(
        project_id,
        {
            "audience_reviews_json": reviews_map,
            "progress_percent": max(project.get("progress_percent", 0), 35),
        },
    )
    return {"success": True, "audience_reviews": reviews_map, "project": updated}


class TriggerAutoPilotPayload(BaseModel):
    speaker: Optional[str] = "vipul_hi_social"
    pace: Optional[float] = 1.05
    bgm_style: Optional[str] = None
    pipeline_mode: Optional[str] = "cinematic"
    auto_upload: Optional[bool] = True


class QuickAutoGeneratePayload(BaseModel):
    movie_titles: Optional[List[str]] = Field(default_factory=list)
    category: Optional[str] = ""
    count: Optional[int] = 3
    speaker: Optional[str] = "vipul_hi_social"
    pace: Optional[float] = 1.05
    bgm_style: Optional[str] = None
    pipeline_mode: Optional[str] = "cinematic"
    auto_upload: Optional[bool] = True


@router.post("/{project_id}/auto-pilot")
def trigger_auto_pilot(project_id: int, payload: Optional[TriggerAutoPilotPayload] = None) -> Dict[str, Any]:
    """Execute complete autonomous 1-click generation pipeline for an existing project."""
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    speaker = payload.speaker if payload and payload.speaker else "vipul_hi_social"
    pace = payload.pace if payload and payload.pace else 1.05
    bgm_style = payload.bgm_style if payload else None
    pipeline_mode = payload.pipeline_mode if payload and payload.pipeline_mode else "cinematic"
    auto_upload = payload.auto_upload if payload and payload.auto_upload is not None else True

    try:
        res = auto_pilot_service.run_auto_pilot(
            project_id=project_id,
            speaker=speaker,
            pace=pace,
            bgm_style=bgm_style,
            pipeline_mode=pipeline_mode,
            auto_upload=auto_upload,
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/quick-auto-generate")
def quick_auto_generate(payload: QuickAutoGeneratePayload) -> Dict[str, Any]:
    """
    Hands-free short generation:
    1. Finds movies from titles or curated category
    2. Enriches with TMDB trailers/posters
    3. Creates project
    4. Runs full Auto-Pilot pipeline and returns final video
    """
    selected_movies: List[Dict[str, Any]] = []

    # 1. If explicit titles provided, search TMDB for each
    if payload.movie_titles and len(payload.movie_titles) > 0:
        for t in payload.movie_titles[:4]:
            t_clean = t.strip()
            if not t_clean:
                continue
            results = tmdb_service.search_multi(t_clean, media_type="movie")
            if results:
                selected_movies.append(results[0])
            else:
                # Minimal fallback movie object
                selected_movies.append({
                    "title": t_clean,
                    "year": "2024",
                    "overview": f"A captivating cinematic story centered on {t_clean}.",
                    "poster_url": None,
                    "backdrop_url": None,
                    "vote_average": 8.0,
                    "trailers": [],
                })

    # 2. If no titles but category provided, use AI curation
    elif payload.category:
        cat_key = payload.category.strip()
        cnt = min(max(payload.count or 3, 1), 4)
        selected_movies = suggestion_service.suggest_by_category(cat_key, count=cnt)

    if not selected_movies:
        raise HTTPException(
            status_code=400,
            detail="Please provide at least 1 movie title or a valid theme/category.",
        )

    # 3. Create the project
    movie_items = [MovieItem(**m) for m in selected_movies]
    created = create_project(CreateProjectRequest(movies=movie_items))
    proj_id = created["id"]

    # 4. Trigger Auto-Pilot
    speaker = payload.speaker or "vipul_hi_social"
    pace = payload.pace or 1.05
    bgm_style = payload.bgm_style
    pipeline_mode = payload.pipeline_mode or "cinematic"
    auto_upload = payload.auto_upload if payload.auto_upload is not None else True

    try:
        res = auto_pilot_service.run_auto_pilot(
            project_id=proj_id,
            speaker=speaker,
            pace=pace,
            bgm_style=bgm_style,
            pipeline_mode=pipeline_mode,
            auto_upload=auto_upload,
        )
        return res
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
