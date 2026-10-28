import math
import subprocess
import wave
from array import array
from unittest.mock import Mock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.config import settings
from app.routes import bgm_routes
from app.services.bgm_service import BGMService


def test_credit_replacement_and_removal_do_not_accumulate_old_tracks():
    old = {'attribution': 'Old track'}
    data = {'youtube_description': 'My Short\n\nMusic credit:\nOld track'}
    updated = BGMService.credit_description(data, {'enabled': True, 'attribution': 'New track'}, old)
    assert updated['youtube_description'] == 'My Short\n\nMusic credit:\nNew track'
    removed = BGMService.credit_description(updated, {'enabled': False}, {'attribution': 'New track'})
    assert removed['youtube_description'] == 'My Short'


@pytest.mark.parametrize('volume', [-0.1, 1])
def test_invalid_music_volume_is_rejected(volume):
    with pytest.raises(ValueError):
        BGMService.mix_filter(10, volume)


def test_custom_track_cannot_escape_its_project(tmp_path):
    service = BGMService()
    service.bgm_dir = tmp_path / 'music'
    outside = tmp_path / 'unrelated.mp3'
    outside.write_bytes(b'audio')
    with pytest.raises(ValueError):
        service.track_info('custom', {'id': 1, 'bgm_data_json': {'custom_path': str(outside)}})


def test_invalid_audio_upload_is_rejected_and_removed(tmp_path, monkeypatch):
    monkeypatch.setattr(bgm_routes.bgm_service, 'bgm_dir', tmp_path)
    repo = Mock()
    repo.get_by_id.return_value = {'id': 1}
    monkeypatch.setattr(bgm_routes, 'project_repo', repo)
    app = FastAPI()
    app.include_router(bgm_routes.router)
    result = TestClient(app).post('/projects/1/bgm/upload', files={'file': ('fake.wav', b'<html>not audio</html>', 'audio/wav')})
    assert result.status_code == 400
    assert not list(tmp_path.rglob('*.wav'))
    repo.update.assert_not_called()


def test_real_mix_ducks_music_without_halving_voice(tmp_path):
    ffmpeg = settings.ffmpeg_binary
    if not ffmpeg:
        pytest.skip('FFmpeg unavailable')
    voice, music = tmp_path / 'voice.wav', tmp_path / 'music.wav'
    def ff(args):
        subprocess.run([ffmpeg, '-v', 'error', '-y', *args], check=True, capture_output=True, timeout=30)
    ff(['-f', 'lavfi', '-i', r'aevalsrc=0.4*sin(2*PI*880*t)*lt(mod(t\,2)\,1):s=48000:d=4', str(voice)])
    ff(['-f', 'lavfi', '-i', 'sine=frequency=220:sample_rate=48000:duration=4', str(music)])
    def render(duck):
        output = tmp_path / f'mixed_{duck}.wav'
        ff(['-f', 'lavfi', '-i', 'color=s=16x16:d=4', '-i', str(voice), '-i', str(music),
            '-filter_complex', BGMService.mix_filter(4, 0.2, duck), '-map', '[aout]', '-ac', '1',
            '-ar', '48000', '-c:a', 'pcm_s16le', str(output)])
        with wave.open(str(output), 'rb') as file:
            assert file.getnframes() / file.getframerate() == pytest.approx(4, abs=0.02)
            samples = array('h', file.readframes(file.getnframes()))
        return samples
    ducked, plain = render(True), render(False)
    def amplitude(samples, frequency):
        segment = samples[int(.65 * 48000):int(.95 * 48000)]
        real = sum(x * math.cos(2 * math.pi * frequency * n / 48000) for n, x in enumerate(segment))
        imag = sum(x * math.sin(2 * math.pi * frequency * n / 48000) for n, x in enumerate(segment))
        return math.hypot(real, imag) / len(segment)
    # Gentle ducking keeps music audible instead of suppressing it under speech.
    assert 0.65 < amplitude(ducked, 220) / amplitude(plain, 220) < 0.9
    assert amplitude(ducked, 880) == pytest.approx(amplitude(plain, 880), rel=0.02)
