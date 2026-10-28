from unittest.mock import Mock

import pytest

from app.config import settings
from app.services.video_composer_service import VideoComposerService


@pytest.mark.parametrize('failure', ['unknown_source', 'concat_failed'])
def test_invalid_timeline_never_silently_uses_a_full_trailer(tmp_path, monkeypatch, failure):
    monkeypatch.setattr(settings, 'storage_dir', str(tmp_path / 'storage'))
    source, voice = tmp_path / 'trailer.mp4', tmp_path / 'voice.mp3'
    source.write_bytes(b'video')
    voice.write_bytes(b'audio')
    service = VideoComposerService()
    monkeypatch.setattr(service, '_cut_scene_segment', Mock(return_value=True))
    monkeypatch.setattr(service, '_concat_segments', Mock(return_value=False))
    monkeypatch.setattr(service, '_layout_for_source', Mock(return_value=('[0:v]null[v]', {})))
    render = Mock()
    monkeypatch.setattr('app.services.video_composer_service.subprocess.run', render)
    scenes = [{'source_video_path': str(tmp_path / 'other.mp4') if failure == 'unknown_source' else str(source),
               'start_seconds': 10, 'duration_seconds': 4}]
    with pytest.raises((ValueError, RuntimeError)):
        service.compose_shorts_video(1, [str(source)], str(voice), scenes=scenes)
    render.assert_not_called()
