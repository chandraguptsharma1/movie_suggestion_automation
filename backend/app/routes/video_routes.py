from pathlib import Path
from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from app.database import project_repo
from app.config import settings
from app.services.video_composer_service import video_composer_service
from app.services.bgm_service import bgm_service

router = APIRouter(prefix="/projects", tags=["Video"])


class ComposeVideoRequest(BaseModel):
    crop_black_bars: Optional[bool] = True
    foreground_zoom: Optional[float] = Field(default=None, ge=1.0, le=2.0)
    foreground_width: Optional[int] = Field(default=None, ge=320, le=1920)
    include_bgm: Optional[bool] = None
    bgm_style: Optional[str] = None
    bgm_volume: Optional[float] = Field(default=None, ge=0, le=0.5)
    bgm_ducking: Optional[bool] = None


@router.post("/{project_id}/compose-video")
def compose_video(project_id: int, payload: Optional[ComposeVideoRequest] = None) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    thumbnail_path = project.get('thumbnail_path')
    if not thumbnail_path or not Path(thumbnail_path).is_file():
        raise HTTPException(status_code=400, detail="Generate/upload the thumbnail first; it will be added at the end of the Short.")

    sources = project.get("source_videos_json") or []
    if not sources:
        raise HTTPException(status_code=400, detail="No downloaded trailer video clips found.")

    voice_path = project.get("voice_audio_path")
    if not voice_path or not Path(voice_path).exists():
        raise HTTPException(status_code=400, detail="No voiceover audio found. Generate voice first.")

    local_paths = [s.get("local_path") for s in sources if s.get("local_path") and Path(s.get("local_path")).exists()]
    if not local_paths:
        raise HTTPException(status_code=400, detail="Downloaded video clip files missing on disk.")

    crop_black_bars = payload.crop_black_bars if payload and payload.crop_black_bars is not None else True
    foreground_zoom = payload.foreground_zoom if payload else None
    foreground_width = payload.foreground_width if payload else None
    saved = project.get('bgm_data_json') or {}
    include_bgm = payload.include_bgm if payload and payload.include_bgm is not None else saved.get('enabled', True)
    bgm_style = payload.bgm_style if payload and payload.bgm_style else saved.get('style', 'suspense')
    bgm_volume = payload.bgm_volume if payload and payload.bgm_volume is not None else saved.get('volume', 0.35)
    bgm_ducking = payload.bgm_ducking if payload and payload.bgm_ducking is not None else saved.get('ducking', True)

    try:
        scenes = project.get("scenes_json") or []
        captions_path = None
        if (project.get('script_data_json') or {}).get('mode') == 'cinematic':
            captions = settings.final_videos_dir / f'project_{project_id}' / 'cinematic' / 'captions.ass'
            beats = (project.get('script_data_json') or {}).get('cinematic_beats') or []
            if not captions.is_file() or not beats or abs(video_composer_service._probe_video_duration(voice_path) - beats[-1]['end']) > .1:
                raise ValueError('Cinematic captions no longer match narration. Create a cinematic version from the original lineup again.')
            captions_path = str(captions)
        res = video_composer_service.compose_shorts_video(
            project_id=project_id,
            source_video_paths=local_paths,
            voice_audio_path=voice_path,
            scenes=scenes,
            crop_black_bars=crop_black_bars,
            foreground_zoom=foreground_zoom,
            foreground_width=foreground_width,
            include_bgm=include_bgm,
            bgm_style=bgm_style,
            bgm_volume=bgm_volume,
            bgm_ducking=bgm_ducking,
            bgm_project=project,
            thumbnail_path=thumbnail_path,
            captions_path=captions_path,
        )
        updated = project_repo.update(
            project_id,
            {
                "final_video_path": res["output_video_path"],
                "status": "COMPLETED",
                "progress_percent": 100,
                "bgm_data_json": {**saved, **res.get('bgm', {})},
                "script_data_json": bgm_service.credit_description(project.get('script_data_json'), res.get('bgm', {}), saved),
                "thumbnail_data_json": {**(project.get('thumbnail_data_json') or {}), 'video_end_card': res.get('thumbnail_end_card')},
            },
        )
        return {"success": True, "composition": res, "project": updated}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{project_id}/video-stream")
def stream_final_video(project_id: int):
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    vid_path = project.get("final_video_path")
    if not vid_path or not Path(vid_path).exists():
        raise HTTPException(status_code=404, detail="Rendered video not found.")

    return FileResponse(path=vid_path, media_type="video/mp4", filename=Path(vid_path).name)
