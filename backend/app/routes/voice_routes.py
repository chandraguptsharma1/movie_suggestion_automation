from pathlib import Path
from typing import Any, Dict
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from app.config import settings
from app.database import project_repo
from app.models.schemas import GenerateVoiceRequest
from app.services.sarvam_tts_service import sarvam_tts_service

router = APIRouter(prefix="/projects", tags=["Voice"])


@router.post("/{project_id}/generate-voice")
def generate_voice(project_id: int, payload: GenerateVoiceRequest) -> Dict[str, Any]:
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    script_text = project.get("script_text") or ""
    if not script_text.strip():
        raise HTTPException(status_code=400, detail="Please generate or write a script first.")

    out_file = settings.audio_dir / f"project_{project_id}" / "voice.mp3"
    try:
        res = sarvam_tts_service.generate_audio(
            text=script_text,
            output_path=str(out_file),
            speaker=payload.speaker or "vipul_hi_social",
            pace=payload.pace or 1.05,
        )
        updated = project_repo.update(
            project_id,
            {
                "voice_audio_path": res["audio_path"],
                "voice_data_json": res,
                "status": "VOICE_READY",
                "progress_percent": max(project.get("progress_percent", 0), 65),
            },
        )
        return {"success": True, "voice": res, "project": updated}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/{project_id}/voice-audio")
def get_voice_audio(project_id: int):
    project = project_repo.get_by_id(project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    audio_path = project.get("voice_audio_path")
    if not audio_path or not Path(audio_path).exists():
        raise HTTPException(status_code=404, detail="Voice audio file not generated or not found.")

    return FileResponse(
        path=audio_path,
        media_type="audio/mpeg" if audio_path.endswith(".mp3") else "audio/wav",
        filename=Path(audio_path).name,
    )
