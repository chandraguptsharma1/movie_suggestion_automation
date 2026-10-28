import re
import uuid
import shutil
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from app.config import settings
from app.database import project_repo
from app.models.schemas import DownloadTrailerRequest
from app.services.trailer_downloader_service import trailer_downloader_service

router = APIRouter(prefix="/projects", tags=["Trailers"])


@router.post("/{project_id}/download-trailer")
def download_trailer(project_id: int, payload: DownloadTrailerRequest) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    res = None
    try:
        res = trailer_downloader_service.download_trailer(
            youtube_url=payload.youtube_url,
            project_id=project_id,
            movie_title=payload.movie_title or "trailer",
            label=payload.label or "",
        )
    except Exception as exc:
        # If YouTube blocks cloud datacenter IP, auto-fallback to cinematic backdrop motion teaser
        target_movie = None
        for m in project.get("movies_json", []):
            if m.get("title", "").strip().lower() == (payload.movie_title or "").strip().lower():
                target_movie = m
                break

        img_url = (target_movie.get("backdrop_url") or target_movie.get("poster_url")) if target_movie else None
        if img_url:
            try:
                res = trailer_downloader_service.create_cinematic_motion_teaser(
                    image_url=img_url,
                    project_id=project_id,
                    movie_title=payload.movie_title or "movie",
                    label=payload.label or f"cinematic_{uuid.uuid4().hex[:6]}",
                )
            except Exception as e2:
                raise HTTPException(status_code=500, detail=f"YouTube blocked ({exc}) and teaser fallback failed ({e2})")
        else:
            raise HTTPException(status_code=500, detail=str(exc))

    sources = project.get("source_videos_json") or []
    sources.append(res)
    updated = project_repo.update(
        project_id,
        {
            "source_videos_json": sources,
            "progress_percent": max(project.get("progress_percent", 0), 60),
        },
    )
    return {"success": True, "downloaded": res, "project": updated}


@router.post("/{project_id}/download-all-trailers")
def download_all_trailers(project_id: int) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    from app.services.auto_pilot_service import auto_pilot_service
    original_paths = {s.get("local_path") for s in project.get("source_videos_json") or []}
    try:
        updated = auto_pilot_service._acquire_trailers(project)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    downloaded = [s for s in updated.get("source_videos_json") or [] if s.get("local_path") not in original_paths]
    warnings = []
    for slot, movie in enumerate(updated.get("movies_json") or [], 1):
        target = min(3, len(movie.get("trailers") or []))
        count = sum(s.get("movie_slot") == slot or s.get("movie_title") == movie.get("title")
                    for s in updated.get("source_videos_json") or [])
        if count < target:
            warnings.append(f"{movie.get('title')}: {count}/{target} trailers acquired; other links could not be downloaded.")
    return {"success": True, "downloaded": downloaded, "errors": warnings, "project": updated}


@router.post("/{project_id}/generate-all-motion-teasers")
def generate_all_motion_teasers(project_id: int) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found. Please create a new project in the studio.")

    movies = project.get("movies_json") or []
    downloaded = []
    errors = []

    for m in movies:
        title = m.get("title") or "Movie"
        backdrop_url = m.get("backdrop_url") or m.get("poster_url")
        if backdrop_url:
            try:
                res = trailer_downloader_service.create_cinematic_motion_teaser(
                    image_url=backdrop_url,
                    project_id=project_id,
                    movie_title=title,
                    label=f"motion_{title[:15]}",
                )
                downloaded.append(res)
            except Exception as exc:
                errors.append(f"{title}: {exc}")
        else:
            errors.append(f"{title}: No backdrop image available")

    existing = project.get("source_videos_json") or []
    existing.extend(downloaded)

    updated = project_repo.update(
        project_id,
        {
            "source_videos_json": existing,
            "progress_percent": max(project.get("progress_percent", 0), 75),
        },
    )

    return {"success": True, "downloaded": downloaded, "errors": errors, "project": updated}


@router.post("/{project_id}/upload-clip")
async def upload_clip(
    project_id: int,
    file: UploadFile = File(...),
    movie_title: str = Form(""),
    label: str = Form(""),
) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    target_dir = settings.source_videos_dir / f"project_{project_id}"
    target_dir.mkdir(parents=True, exist_ok=True)

    clean_name = re.sub(r"[^a-zA-Z0-9_\.]+", "_", file.filename or "uploaded.mp4")
    out_path = target_dir / f"clip_{uuid.uuid4().hex[:6]}_{clean_name}"

    with open(out_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    res = {
        "success": True,
        "label": label or clean_name,
        "movie_title": movie_title or (clean_name.split(".")[0]),
        "url": f"/storage/source_videos/project_{project_id}/{out_path.name}",
        "local_path": str(out_path).replace("\\", "/"),
    }

    sources = project.get("source_videos_json") or []
    sources.append(res)
    updated = project_repo.update(
        project_id,
        {
            "source_videos_json": sources,
            "progress_percent": max(project.get("progress_percent", 0), 60),
        },
    )
    return {"success": True, "downloaded": res, "project": updated}
