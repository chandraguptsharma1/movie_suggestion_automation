from unittest.mock import patch, MagicMock
from pathlib import Path
from app.services.video_composer_service import video_composer_service
from app.services.bgm_service import bgm_service


def test_bgm_catalog_has_tracks():
    from app.services.bgm_service import BGM_CATALOG
    assert "suspense" in BGM_CATALOG
    assert "epic" in BGM_CATALOG
    assert "ambient" in BGM_CATALOG
    assert BGM_CATALOG["suspense"]["filename"].endswith(".mp3")


def test_compose_shorts_includes_bgm_in_ffmpeg_call(tmp_path):
    mock_source = tmp_path / "source.mp4"
    mock_source.write_bytes(b"dummy video data")

    mock_voice = tmp_path / "voice.mp3"
    mock_voice.write_bytes(b"dummy voice data")

    mock_bgm = tmp_path / "suspense.mp3"
    mock_bgm.write_bytes(b"dummy bgm data")

    with patch("subprocess.run") as mock_run, \
         patch.object(bgm_service, "get_bgm_track", return_value=str(mock_bgm)), \
         patch.object(video_composer_service, "detect_crop_area", return_value={"detected": False, "crop_applied": False, "crop_method": "none", "crop_w": 1920, "crop_h": 1080, "crop_x": 0, "crop_y": 0}):

        def finish_render(command, **kwargs):
            if '-filter_complex' in command:
                Path(command[-1]).write_bytes(b'completed render')
            return MagicMock()
        mock_run.side_effect = finish_render

        res = video_composer_service.compose_shorts_video(
            project_id=99,
            source_video_paths=[str(mock_source)],
            voice_audio_path=str(mock_voice),
            include_bgm=True,
            bgm_style="suspense",
            bgm_volume=0.12,
        )

        assert res["success"] is True
        assert res["bgm_mixed"] is True
        assert res["bgm_style"] == "suspense"

        # Check ffmpeg command args in subprocess.run call
        called_cmd = mock_run.call_args[0][0]
        # BGM file should be passed as an input
        assert str(mock_bgm) in called_cmd
        # amix filter should be present in the filter_complex
        filter_str = called_cmd[called_cmd.index("-filter_complex") + 1]
        assert "amix=inputs=2:duration=first" in filter_str
        assert "volume=0.12" in filter_str
