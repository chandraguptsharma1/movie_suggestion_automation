from fastapi import APIRouter, HTTPException
from app.services.cinematic_review_service import cinematic_review_service

router = APIRouter(prefix='/projects', tags=['Cinematic Review'])


@router.post('/{project_id}/cinematic-review')
def cinematic_review(project_id: int):
    try:
        return cinematic_review_service.start(project_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
