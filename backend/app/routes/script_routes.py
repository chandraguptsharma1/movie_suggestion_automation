from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from app.database import project_repo
from app.models.schemas import GenerateScriptRequest, UpdateScriptRequest
from app.services.script_service import script_service

router = APIRouter(prefix="/projects", tags=["Scripts"])


@router.post("/{project_id}/generate-script")
def generate_script(project_id: int, payload: GenerateScriptRequest) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    movies = project.get("movies_json") or []
    if not movies:
        raise HTTPException(status_code=400, detail="No movies in this project.")

    audience_reviews = project.get("audience_reviews_json") or {}

    try:
        script_data = script_service.generate_shorts_script(
            project_title=project.get("title", "Top Movies"),
            movies=movies,
            audience_reviews=audience_reviews,
            creator_notes=payload.creator_notes or project.get("notes", ""),
        )
        full_script = script_data.get("full_script") or ""
        updated = project_repo.update(
            project_id,
            {
                "script_text": full_script,
                "script_data_json": script_data,
                "status": "SCRIPT_READY",
                "progress_percent": max(project.get("progress_percent", 0), 50),
            },
        )
        return {"success": True, "script_data": script_data, "project": updated}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.put("/{project_id}/script")
def update_script(project_id: int, payload: UpdateScriptRequest) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    current_data = project.get("script_data_json") or {}
    if payload.script_data:
        current_data.update(payload.script_data)
    current_data["full_script"] = payload.script_text

    updated = project_repo.update(
        project_id,
        {
            "script_text": payload.script_text,
            "script_data_json": current_data,
        },
    )
    return {"success": True, "project": updated}
