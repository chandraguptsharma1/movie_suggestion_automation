import math
import pytest
from app.services.cinematic_review_service import build_timeline, validate_plan, write_captions


def test_timeline_is_frame_aligned_and_never_exceeds_scene_bounds():
    catalog = [{'start_seconds': 4.1, 'duration_seconds': 2.73}, {'start_seconds': 9, 'duration_seconds': 3.8}]
    beats = [{'kind': 'hook', 'scene_ids': [0, 1]}, {'kind': 'setup', 'scene_ids': [1, 0]}]
    durations = [6.131, 5.294]
    clips, timed = build_timeline(beats, catalog, durations)
    assert sum(s['duration_seconds'] for s in clips) == pytest.approx(timed[-1]['end'])
    assert timed[1]['start'] == timed[0]['end']
    for i, beat in enumerate(timed):
        assert beat['end'] - beat['start'] == pytest.approx(math.ceil((durations[i] + .16) * 30) / 30)
        assert beat['speech_end'] <= beat['end']
    for clip in clips:
        original = next(s for s in catalog if s['start_seconds'] == clip['start_seconds'])
        assert clip['duration_seconds'] <= original['duration_seconds']
        assert clip['end_seconds'] <= original['start_seconds'] + original['duration_seconds']


def test_plan_rejects_hallucinated_scene_ids():
    beats = [{'kind': 'hook' if i == 0 else 'verdict', 'narration': 'यह एक कहानी है ' * 4, 'scene_ids': [99]} for i in range(6)]
    with pytest.raises(ValueError, match='unavailable scene'):
        validate_plan({'beats': beats}, [{}])


def test_timeline_avoids_flash_frames_at_beat_end():
    clips, timed = build_timeline([{'kind': 'setup', 'scene_ids': [0, 1]}],
        [{'start_seconds': 0, 'duration_seconds': 4}, {'start_seconds': 5, 'duration_seconds': 4}], [3.65])
    assert min(c['duration_seconds'] for c in clips) >= .8
    assert sum(c['duration_seconds'] for c in clips) == pytest.approx(timed[-1]['end'])


def test_captions_sanitize_ass_commands_and_end_before_endcard(tmp_path):
    target = tmp_path / 'captions.ass'
    write_captions(target, '{\\pos(0,0)}MOVIE', [{'kind': 'hook', 'narration': 'एक शहर आखिरी उम्मीद',
        'start': 0, 'speech_end': 3.22, 'end': 3.4}])
    text = target.read_text('utf-8-sig')
    assert '{\\pos(0,0)}' not in text
    assert 'Nirmala UI' in text
    assert 'एक शहर' in text
    assert '0:00:03.40,Chapter' in text
    assert '0:00:03.22,Caption' in text


def test_cinematic_effects_keep_narration_timing_and_render(tmp_path, monkeypatch):
    import subprocess
    from PIL import Image, ImageStat
    from app.config import settings
    from app.services.video_composer_service import VideoComposerService
    monkeypatch.setattr(settings, 'storage_dir', str(tmp_path / 'storage'))
    monkeypatch.setattr(settings, 'shorts_width', 180)
    monkeypatch.setattr(settings, 'shorts_height', 320)
    def ff(*args):
        subprocess.run([settings.ffmpeg_binary, '-hide_banner', '-loglevel', 'error', '-y', *args],
                       check=True, capture_output=True, timeout=45)
    source, voice, thumb = tmp_path / 'source.mp4', tmp_path / 'voice.wav', tmp_path / 'thumb.jpg'
    ff('-f', 'lavfi', '-i', 'testsrc2=s=180x320:r=30:d=2', '-c:v', 'libx264', str(source))
    ff('-f', 'lavfi', '-i', 'sine=frequency=440:duration=2', str(voice))
    Image.new('RGB', (180, 320), 'yellow').save(thumb)
    captions = tmp_path / 'captions.ass'
    write_captions(captions, 'TEST', [{'kind': 'hook', 'narration': 'आखिरी उम्मीद', 'start': 0, 'end': 2, 'speech_end': 2}])
    service = VideoComposerService()
    result = service.compose_shorts_video(99, [str(source)], str(voice), include_bgm=False, thumbnail_path=str(thumb),
        captions_path=str(captions), scenes=[{'source_video_path': str(source), 'start_seconds': i,
        'duration_seconds': 1, 'playback_speed': .75, 'cinematic_motion': 'push_in', 'cinematic_grade': True,
        'cinematic_fade_in': True, 'cinematic_fade_out': True} for i in (0, 1)])
    output = result['output_video_path']
    assert service._probe_video_duration(output) == pytest.approx(4, abs=.1)
    segment = settings.final_videos_dir / 'project_99' / 'segments' / 'scene_00.mp4'
    assert service._probe_video_duration(str(segment)) == pytest.approx(1, abs=.04)
    brightness = []
    for when in (0, .5):
        frame = tmp_path / f'frame_{when}.png'
        ff('-ss', str(when), '-i', str(segment), '-frames:v', '1', str(frame))
        with Image.open(frame) as image:
            brightness.append(ImageStat.Stat(image.convert('L')).mean[0])
    assert brightness[0] < 5 and brightness[1] > 20
    ff('-i', output, '-f', 'null', '-')
