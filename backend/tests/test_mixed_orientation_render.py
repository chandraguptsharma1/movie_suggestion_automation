import subprocess
from pathlib import Path

import pytest
from PIL import Image

from app.config import settings
from app.services.video_composer_service import VideoComposerService


def ff(*args):
    subprocess.run([settings.ffmpeg_binary, '-hide_banner', '-loglevel', 'error', '-y', *args],
                   capture_output=True, check=True, timeout=40)


def test_mixed_landscape_portrait_timeline_renders_through_all_clips(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'storage_dir', str(tmp_path / 'storage'))
    monkeypatch.setattr(settings, 'shorts_width', 180)
    monkeypatch.setattr(settings, 'shorts_height', 320)
    monkeypatch.setattr(settings, 'shorts_background_blur', 8)
    blue, green, red = [tmp_path / f'{name}.mp4' for name in ('blue', 'green', 'red')]
    for path, color, size in [(blue, 'blue', '192x108'), (green, 'lime', '108x192'), (red, 'red', '256x144')]:
        ff('-f', 'lavfi', '-i', f'color=c={color}:s={size}:r=30:d=1', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(path))
    voice = tmp_path / 'voice.wav'
    ff('-f', 'lavfi', '-i', 'sine=frequency=440:duration=3', str(voice))
    thumbnail = tmp_path / 'thumbnail.jpg'
    Image.new('RGB', (180, 320), 'yellow').save(thumbnail)
    service = VideoComposerService()
    result = service.compose_shorts_video(1, [str(blue), str(green), str(red)], str(voice),
        scenes=[{'source_video_path': str(path), 'start_seconds': 0, 'duration_seconds': 1} for path in (blue, green, red)],
        include_bgm=False, thumbnail_path=str(thumbnail))
    output = result['output_video_path']
    assert service._probe_video_duration(output) == pytest.approx(5, abs=.1)
    assert service._probe_video_dimensions(output) == (180, 320)
    for when, channel in [(.4, 2), (1.4, 1), (2.4, 0)]:
        frame = tmp_path / f'{when}.png'
        ff('-ss', str(when), '-i', output, '-frames:v', '1', str(frame))
        with Image.open(frame) as image:
            assert image.convert('RGB').getpixel((90, 160))[channel] > 200
    ff('-v', 'error', '-i', output, '-f', 'null', '-')
    assert {service._probe_video_dimensions(str(path)) for path in (Path(output).parent / 'segments').glob('*.mp4')} == {(180, 320)}


def test_error_summary_shows_filter_failure_instead_of_version_banner():
    stderr = ('ffmpeg version 8.1\nconfiguration: ' + 'x' * 600 +
              '\n[Parsed_crop] Invalid too big size for width 1920\nError reinitializing filters!\nConversion failed!')
    result = VideoComposerService._ffmpeg_error(stderr.encode())
    assert 'Invalid too big size' in result
    assert 'ffmpeg version' not in result


def test_failed_recompose_preserves_previous_export(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, 'storage_dir', str(tmp_path / 'storage'))
    service = VideoComposerService()
    source, voice = tmp_path / 'source.mp4', tmp_path / 'voice.wav'
    source.write_bytes(b'source')
    voice.write_bytes(b'voice')
    output = settings.final_videos_dir / 'project_1' / 'shorts_project_1.mp4'
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(b'previous good video')
    monkeypatch.setattr(service, '_probe_video_dimensions', lambda _: (1920, 1080))
    monkeypatch.setattr(service, '_probe_video_duration', lambda _: 1)
    def fail(command, **kwargs):
        Path(command[-1]).write_bytes(b'partial failed video')
        raise subprocess.CalledProcessError(1, command, stderr=b'Error reinitializing filters!')
    monkeypatch.setattr(subprocess, 'run', fail)
    with pytest.raises(RuntimeError, match='Error reinitializing'):
        service.compose_shorts_video(1, [str(source)], str(voice), include_bgm=False, crop_black_bars=False)
    assert output.read_bytes() == b'previous good video'
    assert not list(output.parent.glob('.render_*.mp4'))
    assert 'Error reinitializing' in (output.parent / 'render_error.log').read_text()
