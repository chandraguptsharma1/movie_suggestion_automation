from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import MovieItem
from app.routes.youtube_security import require_local_request
from app.services.processing_queue_service import processing_queue
from app.database import project_repo

router = APIRouter(prefix='/processing-queue', tags=['Processing queue'], dependencies=[Depends(require_local_request)])


@router.get('')
def list_queue():
    return processing_queue.list()


@router.post('')
def add_to_queue(movie: MovieItem):
    if not movie.title.strip():
        raise HTTPException(status_code=400, detail='Select a movie first.')
    return processing_queue.enqueue(movie.model_dump())


@router.post('/{job_id}/retry')
def retry_queue(job_id: int):
    try:
        processing_queue.retry(job_id)
        return {'success': True}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/project/{project_id}')
def queue_existing_project(project_id: int):
    project = project_repo.get_by_id(project_id)
    if not project or len(project.get('movies_json') or []) != 1:
        raise HTTPException(status_code=400, detail='Select a single-movie project.')
    return processing_queue.enqueue(project['movies_json'][0], project_id)
