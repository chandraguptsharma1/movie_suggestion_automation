from typing import Literal
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from app.routes.youtube_security import require_local_request
from app.routes.youtube_upload_routes import UploadRequest, call
from app.services.publishing_automation_service import publishing_automation as service

router = APIRouter(prefix='/publishing-automation', tags=['publishing-automation'],
                   dependencies=[Depends(require_local_request)])


class StudioEvidence(BaseModel):
    video_id: str = Field(min_length=1, max_length=100)
    observed_at: str
    copyright_status: Literal['clear', 'pending', 'claim', 'blocked', 'unknown']
    checks_complete: bool = False
    thumbnail_matches: bool = False
    details: str = Field(min_length=1, max_length=3000)


@router.get('')
def list_jobs():
    return service.list()


@router.get('/{project_id}')
def get_job(project_id: int):
    return {'automation': service.get(project_id)}


@router.post('/{project_id}')
def enable(project_id: int, payload: UploadRequest | None = None):
    return call(service.enable, project_id, payload.model_dump() if payload else None)


@router.post('/{project_id}/studio-evidence')
def evidence(project_id: int, payload: StudioEvidence):
    return call(service.record_studio_evidence, project_id, payload.model_dump())
