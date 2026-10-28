import logging
from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.services.youtube_upload_service import youtube_upload_service as service
from app.routes.youtube_security import require_local_request

router = APIRouter(prefix='/youtube-upload', tags=['youtube-upload'], dependencies=[Depends(require_local_request)])
logger = logging.getLogger(__name__)


class UploadRequest(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    description: str = Field(default='', max_length=5000)
    tags: list[str] = Field(default_factory=list, max_length=100)
    category_id: str = '1'
    made_for_kids: bool


class PublishRequest(BaseModel):
    studio_review_confirmed: bool = False
    thumbnail_review_confirmed: bool = False
    publish_at: str | None = None


@router.get('/account')
def account():
    return service.account()


def call(action, *args, **kwargs):
    try:
        return action(*args, **kwargs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception('YouTube upload operation failed')
        raise HTTPException(status_code=502, detail=service._error_message(exc)) from exc


@router.get('/{movie_id}/preflight')
def preflight(movie_id: int):
    return call(service.preflight, movie_id)


@router.get('/{movie_id}')
def status(movie_id: int):
    return {'job': call(service.status, movie_id)}


@router.post('/{movie_id}')
def start(movie_id: int, payload: UploadRequest):
    return call(service.start, movie_id, payload.model_dump())


@router.post('/{movie_id}/resume')
def resume(movie_id: int):
    return call(service.resume, movie_id)


@router.post('/{movie_id}/refresh')
def refresh(movie_id: int):
    return call(service.refresh, movie_id)


@router.post('/{movie_id}/thumbnail')
def retry_thumbnail(movie_id: int):
    return call(service.retry_thumbnail, movie_id)


@router.get('/{movie_id}/thumbnail')
def thumbnail(movie_id: int):
    path = service._directory(movie_id) / 'thumbnail.jpg'
    if not path.is_file():
        raise HTTPException(status_code=404, detail='Ending frame abhi ready nahi hai.')
    return FileResponse(path, media_type='image/jpeg', filename='youtube-ending-thumbnail.jpg')


@router.post('/{movie_id}/publish')
def publish(movie_id: int, payload: PublishRequest):
    return call(service.publish, movie_id, payload.studio_review_confirmed,
                payload.publish_at, payload.thumbnail_review_confirmed)


@router.get('/{movie_id}/schedule-preview')
def schedule_preview(movie_id: int):
    return call(service.schedule_preview, movie_id)
