import logging
import mimetypes
from pathlib import Path
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.database import project_repo
from app.services.gemini_scene_service import gemini_scene_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/projects", tags=["Scenes"])


@router.get("/{project_id}/source-video/{source_index}")
def preview_source_video(project_id: int, source_index: int):
    project = project_repo.get_by_id(project_id)
    sources = (project or {}).get("source_videos_json") or []
    if not project or source_index < 0 or source_index >= len(sources):
        raise HTTPException(status_code=404, detail="Source trailer not found")
    path = Path(sources[source_index].get("local_path") or "")
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Source trailer file missing")
    return FileResponse(path, media_type=mimetypes.guess_type(str(path))[0] or "video/mp4")


class SceneItemModel(BaseModel):
    slot: int = 1
    movie_title: str
    source_video_path: Optional[str] = ""
    start: str
    end: str
    start_seconds: float
    end_seconds: float
    duration_seconds: float
    scene_type: str = "action_peak"
    visual_energy: str = "high"
    reason: str = ""


class UpdateScenesPayload(BaseModel):
    scenes: List[Dict[str, Any]] = Field(default_factory=list)


@router.post("/{project_id}/select-scenes")
def select_scenes(project_id: int) -> Dict[str, Any]:
    """Analyze trailers using Gemini to select high-energy non-logo scene clips."""
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    source_videos = project.get("source_videos_json") or []
    if not source_videos:
        raise HTTPException(
            status_code=400,
            detail="No downloaded trailers found. Please download trailers before selecting scenes.",
        )

    try:
        scenes = gemini_scene_service.select_scenes_for_project(project)
        if not scenes:
            raise HTTPException(
                status_code=500,
                detail="Scene selection could not produce valid clips from the available trailers.",
            )

        new_progress = max(project.get("progress_percent", 0), 75)
        updated = project_repo.update(
            project_id,
            {
                "scenes_json": scenes,
                "progress_percent": new_progress,
            },
        )
        return {
            "success": True,
            "scenes": scenes,
            "project": updated,
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Error selecting scenes with Gemini for project %s: %s", project_id, exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{project_id}/scenes")
def get_scenes(project_id: int) -> Dict[str, Any]:
    """Get the current selected scene list for a project."""
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    scenes = project.get("scenes_json") or []
    return {"scenes": scenes}


@router.put("/{project_id}/scenes")
def update_scenes(project_id: int, payload: UpdateScenesPayload) -> Dict[str, Any]:
    """Update or customize the scene timings and order for a project."""
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    updated = project_repo.update(
        project_id,
        {
            "scenes_json": payload.scenes,
        },
    )
    return {
        "success": True,
        "scenes": payload.scenes,
        "project": updated,
    }
