from copy import deepcopy
import shutil
import subprocess
from unittest.mock import Mock

import pytest

from app.services import auto_pilot_service as module
from app.services.auto_pilot_service import AutoPilotService


@pytest.fixture
def pipeline(monkeypatch):
    project = {"id": 42, "movies_json": [{"title": "First", "tmdb_id": 1}], "source_videos_json": []}
    repo = Mock()
    repo.get_by_id.side_effect = lambda _: deepcopy(project)

    def update(_, changes):
        project.update(deepcopy(changes))
        return deepcopy(project)

    repo.update.side_effect = update
    monkeypatch.setattr(module, "project_repo", repo)
    downloader = Mock()
    monkeypatch.setattr(module, "trailer_downloader_service", downloader)
    tmdb = Mock()
    tmdb.fetch_videos.return_value = []
    monkeypatch.setattr(module, "tmdb_service", tmdb)
    script = Mock()
    monkeypatch.setattr(module, "script_service", script)
    service = AutoPilotService()
    monkeypatch.setattr(service, "_is_playable_source", lambda s: s.get("local_path") == "valid.mp4" and not s.get("is_fallback"))
    return service, project, downloader, tmdb, script


def test_refresh_missing_trailers_and_try_next_candidate(pipeline):
    service, project, downloader, tmdb, _ = pipeline
    tmdb.fetch_videos.return_value = [{"url": "bad"}, {"url": "good"}]
    downloader.download_trailer.side_effect = [RuntimeError("unavailable"), {"local_path": "valid.mp4", "movie_title": "First"}]
    updated = service._acquire_trailers(project)
    tmdb.fetch_videos.assert_called_once_with(1, "movie", strict=True)
    assert [c.kwargs["youtube_url"] for c in downloader.download_trailer.call_args_list] == ["bad", "good"]
    assert updated["source_videos_json"][0]["movie_slot"] == 1
    assert len(updated["trailers_json"]) == 2
    downloader.create_cinematic_motion_teaser.assert_not_called()


def test_missing_movie_blocks_all_later_steps_and_preserves_download(pipeline):
    service, project, downloader, tmdb, script = pipeline
    project["movies_json"].append({"title": "Second", "tmdb_id": 2})
    tmdb.fetch_videos.side_effect = [[{"url": "good"}], []]
    downloader.download_trailer.return_value = {"local_path": "valid.mp4", "movie_title": "First"}
    with pytest.raises(RuntimeError, match="Second"):
        service.run_auto_pilot(42)
    assert project["status"] == "TRAILERS_REQUIRED"
    assert project["progress_percent"] == 15
    assert len(project["source_videos_json"]) == 1
    script.generate_shorts_script.assert_not_called()
    downloader.create_cinematic_motion_teaser.assert_not_called()
    # A retry must preserve the successful movie and try only the missing movie.
    tmdb.fetch_videos.reset_mock(side_effect=True)
    tmdb.fetch_videos.return_value = []
    with pytest.raises(RuntimeError):
        service.run_auto_pilot(42)
    tmdb.fetch_videos.assert_called_once_with(2, "movie", strict=True)


@pytest.mark.parametrize("old_source", [
    {"movie_title": "First", "local_path": "deleted.mp4"},
    {"movie_title": "First", "local_path": "valid.mp4", "is_fallback": True},
])
def test_stale_or_motion_sources_do_not_bypass_gate(pipeline, old_source):
    service, project, downloader, tmdb, script = pipeline
    project["source_videos_json"] = [old_source]
    with pytest.raises(RuntimeError, match="Trailers required"):
        service.run_auto_pilot(42)
    tmdb.fetch_videos.assert_called_once()
    script.generate_shorts_script.assert_not_called()


def test_valid_existing_clip_needs_no_download(pipeline):
    service, project, downloader, tmdb, _ = pipeline
    project["source_videos_json"] = [{"movie_title": "First", "local_path": "valid.mp4"}]
    service._acquire_trailers(project)
    downloader.download_trailer.assert_not_called()
    tmdb.fetch_videos.assert_not_called()


def test_three_available_trailers_are_downloaded_before_selection(pipeline, monkeypatch):
    service, project, downloader, tmdb, _ = pipeline
    monkeypatch.setattr(service, '_is_playable_source', lambda _: True)
    tmdb.fetch_videos.return_value = [{'url': f'url{i}'} for i in range(3)]
    downloader.download_trailer.side_effect = [
        {'local_path': f'clip{i}.mp4', 'movie_title': 'First'} for i in range(3)
    ]
    result = service._acquire_trailers(project)
    assert len(result['source_videos_json']) == 3
    assert downloader.download_trailer.call_count == 3


def test_invalid_download_does_not_reach_script(pipeline):
    service, project, downloader, tmdb, script = pipeline
    tmdb.fetch_videos.return_value = [{"url": "bad"}]
    downloader.download_trailer.return_value = {"local_path": "empty.mp4"}
    with pytest.raises(RuntimeError, match="invalid files"):
        service.run_auto_pilot(42)
    script.generate_shorts_script.assert_not_called()


def test_tmdb_connection_error_is_reported(pipeline):
    service, project, _, tmdb, script = pipeline
    tmdb.fetch_videos.side_effect = RuntimeError("TMDB connection failed after 3 attempts.")
    with pytest.raises(RuntimeError, match="TMDB connection failed"):
        service.run_auto_pilot(42)
    assert "TMDB connection failed" in project["notes"]
    script.generate_shorts_script.assert_not_called()


def test_pipeline_continues_after_every_trailer_is_verified(pipeline, monkeypatch):
    service, project, downloader, tmdb, script = pipeline
    tmdb.fetch_videos.return_value = [{"url": "good"}]
    downloader.download_trailer.return_value = {"local_path": "valid.mp4", "movie_title": "First"}

    def generate_script(**kwargs):
        assert len(project["source_videos_json"]) == len(project["movies_json"])
        return {"full_script": "Test script"}

    script.generate_shorts_script.side_effect = generate_script
    monkeypatch.setattr(module, "sarvam_tts_service", Mock(generate_audio=Mock(return_value={"audio_path": "voice.mp3"})))
    monkeypatch.setattr(module, "collage_thumbnail_service", Mock(generate_shorts_collage=Mock(return_value={"output_path": "thumb.jpg"})))
    monkeypatch.setattr(module, "gemini_scene_service", Mock(select_scenes_for_project=Mock(return_value=[{
        "source_video_path": "valid.mp4", "start_seconds": 15, "duration_seconds": 4,
    }])))
    composer = Mock(compose_shorts_video=Mock(return_value={"output_video_path": "final.mp4"}))
    monkeypatch.setattr(module, "video_composer_service", composer)
    # The file probe is already tested separately; keep the pipeline test independent of disk.
    monkeypatch.setattr(module.Path, "exists", lambda _: True)
    result = service.run_auto_pilot(42)
    assert result["success"] is True
    assert project["status"] == "COMPLETED"
    composer.compose_shorts_video.assert_called_once()


def test_probe_accepts_real_video_and_rejects_corrupt_file(tmp_path):
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg or not shutil.which(module.settings.ffprobe_binary):
        pytest.skip("FFmpeg/FFprobe unavailable")
    clip = tmp_path / "trailer.mp4"
    subprocess.run(
        [ffmpeg, "-v", "error", "-f", "lavfi", "-i", "color=c=black:s=32x32:d=1",
         "-c:v", "libx264", str(clip)], check=True, timeout=30,
    )
    service = AutoPilotService()
    assert service._is_playable_source({"local_path": str(clip)})
    assert not service._is_playable_source({"local_path": str(clip), "is_fallback": True})
    corrupt = tmp_path / "corrupt.mp4"
    corrupt.write_bytes(b"not a video")
    assert not service._is_playable_source({"local_path": str(corrupt)})
