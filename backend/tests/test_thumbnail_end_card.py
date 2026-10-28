import subprocess
from pathlib import Path

import pytest
from PIL import Image

from app.config import settings
from app.services.video_composer_service import VideoComposerService
from app.services import video_composer_service as module


def ff(args):
    subprocess.run([settings.ffmpeg_binary, '-v', 'error', '-y', *args], check=True, capture_output=True, timeout=30)


@pytest.fixture
def media(tmp_path):
    if not settings.ffmpeg_binary:
        pytest.skip('FFmpeg unavailable')
    video, voice, image = tmp_path / 'source.mp4', tmp_path / 'voice.wav', tmp_path / 'thumbnail.png'
    ff(['-f', 'lavfi', '-i', 'color=c=blue:s=180x320:r=30:d=1', '-f', 'lavfi', '-i',
        'sine=frequency=440:duration=1', '-c:v', 'libx264', '-c:a', 'aac', '-shortest', str(video)])
    ff(['-f', 'lavfi', '-i', 'sine=frequency=440:duration=1', str(voice)])
    Image.new('RGB', (300, 150), 'red').save(image)
    return video, voice, image


def check_ending(service, path, tmp_path):
    assert service._probe_video_duration(str(path)) == pytest.approx(3, abs=0.1)
    frame = tmp_path / (path.stem + '.png')
    ff(['-ss', '2.5', '-i', str(path), '-frames:v', '1', str(frame)])
    with Image.open(frame) as image:
        red, green, blue = image.convert('RGB').getpixel((90, 160))
        assert red > 200 and green < 40 and blue < 40
        assert max(image.convert('RGB').getpixel((90, 20))) < 10  # Fit, do not crop the thumbnail.
    ff(['-ss', '0.3', '-i', str(path), '-frames:v', '1', str(frame)])
    with Image.open(frame) as image:
        red, green, blue = image.convert('RGB').getpixel((90, 160))
        assert blue > 200 and red < 40


def test_existing_mixed_short_gets_full_ending_image(media, tmp_path):
    video, _, image = media
    output = tmp_path / 'with_ending.mp4'
    service = VideoComposerService()
    result = service.append_thumbnail_end_card(video, image, output)
    assert result['duration_seconds'] == 2
    check_ending(service, output, tmp_path)


def test_replacing_ending_does_not_stack_cards(media, tmp_path):
    video, _, image = media
    service = VideoComposerService()
    first, second = tmp_path / 'first.mp4', tmp_path / 'second.mp4'
    service.append_thumbnail_end_card(video, image, first)
    blue = tmp_path / 'blue.jpg'
    Image.new('RGB', (180, 320), 'lime').save(blue)
    service.append_thumbnail_end_card(first, blue, second, content_duration=1)
    assert service._probe_video_duration(str(second)) == pytest.approx(3, abs=.1)
    frame = tmp_path / 'replaced.png'
    ff(['-ss', '2.5', '-i', str(second), '-frames:v', '1', str(frame)])
    with Image.open(frame) as result:
        assert result.getpixel((90, 160))[1] > 200


@pytest.mark.parametrize('music', [False, True])
def test_composer_appends_thumbnail_with_correct_audio_input(media, tmp_path, monkeypatch, music):
    video, voice, image = media
    monkeypatch.setattr(settings, 'storage_dir', str(tmp_path / 'storage'))
    monkeypatch.setattr(settings, 'shorts_width', 180)
    monkeypatch.setattr(settings, 'shorts_height', 320)
    monkeypatch.setattr(module.bgm_service, 'track_info', lambda *a: {'path': str(voice), 'attribution': 'Test music'})
    service = VideoComposerService()
    result = service.compose_shorts_video(1, [str(video)], str(voice), include_bgm=music, thumbnail_path=str(image))
    assert result['thumbnail_end_card']['starts_at_seconds'] == pytest.approx(1, abs=0.05)
    check_ending(service, Path(result['output_video_path']), tmp_path)


def test_missing_thumbnail_fails_before_render(tmp_path):
    service = VideoComposerService()
    with pytest.raises(ValueError, match='missing'):
        service.append_thumbnail_end_card(tmp_path / 'missing.mp4', tmp_path / 'missing.jpg', tmp_path / 'out.mp4')
