import mimetypes
from pathlib import Path
from uuid import uuid4
from typing import Literal

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from app.database import project_repo
from app.services.bgm_service import BGM_CATALOG, bgm_service

router = APIRouter(tags=["Background music"])


class MusicSettings(BaseModel):
    enabled: bool = True
    style: str = "suspense"
    volume: float = Field(default=0.15, ge=0, le=0.5)
    ducking: bool = True


def project_or_404(project_id):
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/bgm/catalog")
def catalog():
    seen_files = set()
    items = []
    for key in ["suspense", "mystery", "epic", "ambient"]:
        if key in BGM_CATALOG:
            track = BGM_CATALOG[key]
            seen_files.add(track["filename"])
            items.append({
                "style": key,
                "label": track["label"],
                "mood": track.get("mood", ""),
                "license": track.get("license", "YouTube Audio Library (Royalty-free)"),
            })
    for key, track in BGM_CATALOG.items():
        if track["filename"] not in seen_files:
            seen_files.add(track["filename"])
            items.append({
                "style": key,
                "label": track["label"],
                "mood": track.get("mood", ""),
                "license": track.get("license", "YouTube Audio Library (Royalty-free)"),
            })
    return items


@router.get('/projects/{project_id}/bgm/preview/{style}')
def preview(project_id: int, style: str):
    try:
        track = bgm_service.track_info(style, project_or_404(project_id))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FileResponse(track['path'], media_type=mimetypes.guess_type(track['path'])[0] or 'audio/mpeg')


@router.put('/projects/{project_id}/bgm')
def save_settings(project_id: int, payload: MusicSettings):
    project = project_or_404(project_id)
    data = {**(project.get('bgm_data_json') or {}), **payload.model_dump()}
    if payload.enabled and payload.style != 'none':
        try:
            info = bgm_service.track_info(payload.style, {**project, 'bgm_data_json': data})
            data.update({k: v for k, v in info.items() if k != 'path'})
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        data['attribution'] = ''
    updated = project_repo.update(project_id, {'bgm_data_json': data})
    return {'success': True, 'project': updated, 'music': data}


@router.post('/projects/{project_id}/bgm/upload')
def upload(project_id: int, file: UploadFile = File(...), credit: str = Form(default='', max_length=2000)):
    project = project_or_404(project_id)
    if Path(file.filename or '').suffix.lower() not in ('.mp3', '.wav', '.m4a', '.aac', '.ogg', '.flac'):
        raise HTTPException(status_code=400, detail='MP3, WAV, M4A, AAC, OGG ya FLAC upload karein.')
    folder = bgm_service.bgm_dir / f'project_{project_id}'
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f'{uuid4().hex}{Path(file.filename).suffix.lower()}'
    try:
        with path.open('wb') as output:
            size = 0
            while chunk := file.file.read(1024 * 1024):
                size += len(chunk)
                if size > 25 * 1024 * 1024:
                    raise HTTPException(status_code=413, detail='Music file 25 MB se chhoti honi chahiye.')
                output.write(chunk)
        if not bgm_service.is_audio(path):
            raise HTTPException(status_code=400, detail='File mein playable audio nahi hai.')
    except Exception:
        path.unlink(missing_ok=True)
        raise
    data = {**(project.get('bgm_data_json') or {}), 'custom_path': str(path.resolve()),
            'custom_name': Path(file.filename).name, 'custom_credit': credit.strip(),
            'style': 'custom', 'enabled': True, 'volume': 0.15, 'ducking': True,
            'label': Path(file.filename).name, 'attribution': credit.strip(), 'license': 'User-provided; verify usage rights'}
    updated = project_repo.update(project_id, {'bgm_data_json': data})
    return {'success': True, 'project': updated, 'music': data}
