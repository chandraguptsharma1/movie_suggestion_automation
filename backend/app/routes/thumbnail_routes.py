import uuid
from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, Body
from fastapi.responses import FileResponse
import requests
from app.config import settings
from app.database import project_repo
from app.models.schemas import GenerateCollageRequest
from app.services.collage_thumbnail_service import collage_thumbnail_service
from app.services.video_composer_service import video_composer_service

router = APIRouter(prefix="/projects", tags=["Thumbnails"])


@router.post('/{project_id}/update-thumbnail-ending')
def update_thumbnail_ending(project_id: int):
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    video, thumbnail = project.get('final_video_path'), project.get('thumbnail_path')
    if not video or not thumbnail or not Path(video).is_file() or not Path(thumbnail).is_file():
        raise HTTPException(status_code=400, detail='Export video and generate thumbnail first')
    data = project.get('thumbnail_data_json') or {}
    card = data.get('video_end_card') or {}
    output = Path(video).with_name(f'shorts_thumbnail_{uuid.uuid4().hex[:8]}.mp4')
    try:
        result = video_composer_service.append_thumbnail_end_card(video, thumbnail, output,
            content_duration=card.get('starts_at_seconds'))
        updated = project_repo.update(project_id, {'final_video_path': str(output).replace('\\', '/'),
            'thumbnail_data_json': {**data, 'video_end_card': result}})
        return {'success': True, 'project': updated}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/{project_id}/generate-collage")
def generate_collage(project_id: int, payload: GenerateCollageRequest) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    movies = project.get("movies_json") or []
    if not movies:
        raise HTTPException(status_code=400, detail="No movies found in this project.")

    out_file = settings.thumbnails_dir / f"project_{project_id}" / f"collage_{uuid.uuid4().hex[:6]}.jpg"

    try:
        res = collage_thumbnail_service.generate_shorts_collage(
            movies=movies,
            output_path=str(out_file),
            top_text=payload.top_text or "SUPER ADDICTIVE",
            bottom_text=payload.bottom_text or "MASTERPIECES!",
            rating_text=payload.rating_text or "",
            layout=payload.layout,
        )
        old_card = (project.get('thumbnail_data_json') or {}).get('video_end_card')
        if old_card:
            res['video_end_card'] = old_card
        updated = project_repo.update(
            project_id,
            {
                "thumbnail_path": res["output_path"],
                "thumbnail_data_json": res,
                "progress_percent": max(project.get("progress_percent", 0), 85),
            },
        )
        return {"success": True, "thumbnail": res, "project": updated}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/{project_id}/set-poster-thumbnail")
def set_poster_thumbnail(project_id: int, poster_url: str = Body(..., embed=True)) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    out_file = settings.thumbnails_dir / f"project_{project_id}" / f"poster_{uuid.uuid4().hex[:6]}.jpg"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        resp = requests.get(poster_url, timeout=20)
        resp.raise_for_status()
        with out_file.open("wb") as f:
            f.write(resp.content)

        thumb_data = {
            "output_path": str(out_file).replace("\\", "/"),
            "source_url": poster_url,
            "provider": "movie_poster",
        }
        old_card = (project.get('thumbnail_data_json') or {}).get('video_end_card')
        if old_card:
            thumb_data['video_end_card'] = old_card
        updated = project_repo.update(
            project_id,
            {
                "thumbnail_path": thumb_data["output_path"],
                "thumbnail_data_json": thumb_data,
                "progress_percent": max(project.get("progress_percent", 0), 85),
            },
        )
        return {"success": True, "thumbnail": thumb_data, "project": updated}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{project_id}/thumbnail-image")
def get_thumbnail_image(project_id: int):
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    thumb_path = project.get("thumbnail_path")
    if not thumb_path or not Path(thumb_path).exists():
        raise HTTPException(status_code=404, detail="Thumbnail image not found.")

    return FileResponse(path=thumb_path, media_type="image/jpeg", filename=Path(thumb_path).name)
