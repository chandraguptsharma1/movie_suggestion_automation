import pytest
from types import SimpleNamespace
from unittest.mock import Mock

from app.services import gemini_scene_service as module
from app.services.gemini_scene_service import GeminiSceneService


def project_with_sources(tmp_path, count=3):
    sources = []
    for i in range(count):
        path = tmp_path / f'trailer{i}.mp4'
        path.write_bytes(b'video')
        sources.append({'movie_title': 'Runner', 'local_path': str(path), 'label': f'Trailer {i + 1}'})
    voice = tmp_path / 'voice.mp3'
    voice.write_bytes(b'audio')
    return {'movies_json': [{'title': 'Runner'}], 'source_videos_json': sources,
            'voice_audio_path': str(voice), 'script_data_json': {'movie_spotlights': [{'slot': 1, 'duration_sec': 40}]}}


def test_all_three_trailers_are_analyzed_and_balanced_to_voice_duration(tmp_path, monkeypatch):
    service = GeminiSceneService()
    project = project_with_sources(tmp_path)
    monkeypatch.setattr(module, 'get_video_duration', lambda p: 51 if p.endswith('.mp3') else 120)
    analyzed = []

    def select(title, path, target, slot, *args):
        analyzed.append(path)
        return service._generate_fallback_scenes(title, path, 120, target, slot)

    monkeypatch.setattr(service, 'select_scenes_for_movie', select)
    monkeypatch.setattr(service, '_frame_quality', lambda *_: (True, None))
    scenes = service.select_scenes_for_project(project)
    assert len(analyzed) == 3
    assert len(set(s['source_video_path'] for s in scenes)) == 3
    assert sum(s['duration_seconds'] for s in scenes) == pytest.approx(51, abs=0.02)
    assert all(0 < s['duration_seconds'] <= 5 for s in scenes)
    assert scenes[0]['source_video_path'] != scenes[1]['source_video_path']
    for source in analyzed:
        intervals = sorted((s['start_seconds'], s['end_seconds']) for s in scenes if s['source_video_path'] == source)
        assert all(a[1] <= b[0] for a, b in zip(intervals, intervals[1:]))
    project['scenes_json'] = scenes
    assert service.selection_is_current(project)
    project['source_videos_json'][0]['local_path'] = str(tmp_path / 'missing.mp4')
    assert not service.selection_is_current(project)


def test_unrelated_movie_trailer_is_never_substituted(tmp_path):
    project = project_with_sources(tmp_path, 1)
    project['movies_json'] = [{'title': 'Different movie'}]
    with pytest.raises(ValueError, match='Different movie'):
        GeminiSceneService().select_scenes_for_project(project)


def test_short_trailer_fallback_stays_inside_actual_duration():
    scenes = GeminiSceneService()._generate_fallback_scenes('Movie', 'clip.mp4', 6, 20, 1)
    assert scenes
    assert all(0 <= s['start_seconds'] < s['end_seconds'] <= 6 for s in scenes)
    assert all(s['selection_method'] == 'temporal_fallback' for s in scenes)


def test_same_path_is_analyzed_only_once(tmp_path):
    project = project_with_sources(tmp_path, 1)
    project['source_videos_json'] *= 3
    assert len(GeminiSceneService._movie_sources(project, {'title': 'Runner'}, 1)) == 1


def test_invalid_and_overlapping_ai_timings_are_rejected(monkeypatch):
    service = GeminiSceneService()
    monkeypatch.setattr(module, 'get_video_duration', lambda _: 100)
    monkeypatch.setattr(service, '_call_gemini_json', lambda *a, **k: [
        {'start': 'nan', 'end': '25'}, {'start': '20', 'end': '40'},
        {'start': '22', 'end': '26'}, {'start': '95', 'end': '99'},
    ])
    scenes = service.select_scenes_for_movie('Movie', 'clip.mp4', 10, 1)
    assert len(scenes) == 1
    assert scenes[0]['start_seconds'] == 20
    assert scenes[0]['duration_seconds'] == 5


def test_repeated_or_black_frames_are_removed(tmp_path, monkeypatch):
    service = GeminiSceneService()
    project = project_with_sources(tmp_path, 1)
    monkeypatch.setattr(module, 'get_video_duration', lambda p: 30 if p.endswith('.mp3') else 100)
    monkeypatch.setattr(service, 'select_scenes_for_movie', lambda *a, **k: service._generate_fallback_scenes('Runner', a[1], 100, 50, 1))
    hashes = iter([(False, 0), (True, 0xAAAAAAAAAAAAAAAA), (True, 0xAAAAAAAAAAAAAAAA)] +
                  [(True, None)] * 50)
    monkeypatch.setattr(service, '_frame_quality', lambda *_: next(hashes))
    scenes = service.select_scenes_for_project(project)
    assert len(scenes) < 15
    assert scenes[0]['start_seconds'] > 10


def test_failed_video_upload_never_generates_imagined_text_only_scenes(tmp_path, monkeypatch):
    path = tmp_path / 'clip.mp4'
    path.write_bytes(b'video')
    client = Mock()
    client.files.upload.return_value = SimpleNamespace(name='temporary')
    client.files.get.return_value = SimpleNamespace(state='FAILED')
    monkeypatch.setattr(module, 'genai', SimpleNamespace(Client=lambda **_: client))
    service = GeminiSceneService()
    service.api_key = 'test'
    with pytest.raises(RuntimeError, match='could not process'):
        service._call_gemini_json('Analyze video', str(path))
    client.models.generate_content.assert_not_called()
    client.files.delete.assert_called_once_with(name='temporary')
