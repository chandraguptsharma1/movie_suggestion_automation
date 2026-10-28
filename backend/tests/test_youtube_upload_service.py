import json
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
from PIL import Image

from app.services.youtube_upload_service import YouTubeUploadService


def test_transport_returns_resume_incomplete_to_upload_client(service, monkeypatch):
    import app.services.youtube_upload_service as module
    monkeypatch.setattr(module.youtube_oauth_service, 'get_credentials', lambda: Mock())
    factory = Mock()
    monkeypatch.setattr(module, 'build', factory)
    service._youtube()
    transport = factory.call_args.kwargs['http'].http
    assert 308 not in transport.redirect_codes
    assert 301 in transport.redirect_codes
    assert transport.timeout == 60


def test_non_json_upload_error_includes_status_without_private_response():
    from googleapiclient.errors import HttpError
    import httplib2
    exc = HttpError(httplib2.Response({'status': '400'}), b'private-upload-session-url')
    message = YouTubeUploadService._error_message(exc)
    assert 'HTTP 400' in message
    assert 'private-upload' not in message


def test_api_error_retains_reason_code():
    from googleapiclient.errors import HttpError
    import httplib2
    exc = HttpError(httplib2.Response({'status': '403'}), json.dumps({
        'error': {'message': 'Daily quota exceeded', 'errors': [{'reason': 'quotaExceeded'}]}
    }).encode())
    assert 'HTTP 403: Daily quota exceeded (quotaExceeded)' in YouTubeUploadService._error_message(exc)


@pytest.fixture
def service(tmp_path):
    return YouTubeUploadService(root=tmp_path / 'jobs', repository=Mock())


def uploaded(service, **extra):
    job = {'movie_id': 7, 'video_id': 'video123', 'channel_id': 'channel1', 'title': 'Review',
           'state': 'PRIVATE_REVIEW', 'progress': 100, 'thumbnail_state': 'accepted_by_youtube', **extra}
    service._save(job)
    return job


def youtube_status(service, monkeypatch, status=None, processing=None, details=None):
    youtube = Mock()
    youtube.channels().list().execute.return_value = {'items': [{'id': 'channel1', 'contentDetails': {'relatedPlaylists': {'uploads': 'uploads1'}}}]}
    youtube.playlistItems().list().execute.return_value = {'items': []}
    youtube.videos().list().execute.return_value = {'items': [{
        'snippet': {'channelId': 'channel1'},
        'status': status or {'privacyStatus': 'private', 'uploadStatus': 'processed'},
        'processingDetails': processing or {'processingStatus': 'succeeded'},
        'contentDetails': details or {},
    }]}
    monkeypatch.setattr(service, '_youtube', lambda: youtube)
    youtube.videos().update().execute.side_effect = lambda: {
        'status': youtube.videos().update.call_args.kwargs['body']['status']}
    youtube.videos().update.reset_mock()
    return youtube


def test_start_is_private_and_duplicate_requests_reuse_job(service, monkeypatch, tmp_path):
    source = tmp_path / 'source.mp4'
    source.write_bytes(b'video')
    monkeypatch.setattr(service, '_movie_file', lambda _: ({}, source))
    monkeypatch.setattr(service, 'preflight', lambda _: {'ready': True})
    monkeypatch.setattr(service, '_youtube', Mock())
    monkeypatch.setattr(service, 'account', lambda: {'is_authenticated': True})
    launch = Mock()
    monkeypatch.setattr(service, '_launch', launch)
    payload = {'title': 'My review', 'description': 'Description', 'tags': [], 'made_for_kids': False}
    result = service.start(7, payload)
    second = service.start(7, payload)
    assert result['movie_id'] == second['movie_id']
    assert service._load(7)['request_body']['status']['privacyStatus'] == 'private'
    launch.assert_called_once_with(7)


def test_no_copyright_clearance_is_inferred_from_empty_restrictions(service, monkeypatch):
    uploaded(service)
    youtube = youtube_status(service, monkeypatch)
    result = service.refresh(7)
    assert result['copyright_check'] == 'studio_review_required'
    assert result['restriction_detected'] is False
    with pytest.raises(ValueError, match='Checks/Copyright'):
        service.publish(7, False)
    youtube.videos().update.assert_not_called()


def test_api_accepted_thumbnail_still_requires_display_confirmation(service, monkeypatch):
    uploaded(service)
    youtube = youtube_status(service, monkeypatch)
    with pytest.raises(ValueError, match='display confirmation'):
        service.publish(7, True)
    youtube.videos().update.assert_not_called()


def test_retry_uses_latest_project_design_without_reupload(service, monkeypatch, tmp_path):
    uploaded(service)
    youtube = youtube_status(service, monkeypatch)
    source = tmp_path / 'new-design.jpg'
    Image.new('RGB', (1080, 1920), 'green').save(source)
    service.repository.get_by_id.return_value = {'thumbnail_path': str(source)}
    result = service.retry_thumbnail(7)
    with Image.open(service._directory(7) / 'thumbnail.jpg') as image:
        assert image.getpixel((20, 20))[1] > 100
    assert result['thumbnail_source'] == 'latest_project_design'
    assert result['uploaded_video_ending_unchanged']
    assert result['thumbnail_display_confirmation_required']
    assert 'thumbnail_source_path' not in result
    youtube.videos().insert.assert_not_called()


@pytest.mark.parametrize('status,processing,details', [
    ({'uploadStatus': 'rejected', 'rejectionReason': 'copyright'}, None, None),
    (None, {'processingStatus': 'processing'}, None),
    (None, None, {'regionRestriction': {'blocked': ['IN']}}),
    (None, None, {'regionRestriction': {'allowed': []}}),
])
def test_publish_blocked_for_rejection_pending_processing_or_regions(service, monkeypatch, status, processing, details):
    uploaded(service)
    youtube = youtube_status(service, monkeypatch, status, processing, details)
    with pytest.raises(ValueError, match='Processing incomplete'):
        service.publish(7, True)
    youtube.videos().update.assert_not_called()


def test_publish_and_schedule_require_explicit_review(service, monkeypatch):
    uploaded(service)
    youtube = youtube_status(service, monkeypatch)
    result = service.publish(7, True, thumbnail_review_confirmed=True)
    assert result['state'] == 'SCHEDULED'
    status = youtube.videos().update.call_args.kwargs['body']['status']
    assert status['privacyStatus'] == 'private'
    when = datetime.fromisoformat(status['publishAt'])
    assert (when.hour, when.minute) == (13, 0)  # 18:30 IST
    assert when > datetime.now(timezone.utc)


def test_manual_time_cannot_override_fixed_daily_schedule(service, monkeypatch):
    uploaded(service)
    youtube = youtube_status(service, monkeypatch)
    with pytest.raises(ValueError, match='Manual schedule disabled'):
        service.publish(7, True, '2026-10-29T10:00:00Z', thumbnail_review_confirmed=True)
    youtube.videos().update.assert_not_called()


def test_repeated_schedule_keeps_confirmed_slot_without_second_update(service, monkeypatch):
    uploaded(service)
    youtube = youtube_status(service, monkeypatch)
    first = service.publish(7, True, thumbnail_review_confirmed=True)
    youtube.videos().update.reset_mock()
    youtube.videos().list().execute.return_value['items'][0]['status']['publishAt'] = first['publish_at']
    second = service.publish(7, True, thumbnail_review_confirmed=True)
    assert second['publish_at'] == first['publish_at']
    youtube.videos().update.assert_not_called()


def test_thumbnail_failure_does_not_trigger_another_upload(service, monkeypatch):
    uploaded(service, thumbnail_state='needs_attention')
    youtube = youtube_status(service, monkeypatch)
    with pytest.raises(ValueError, match='Thumbnail retry/Studio'):
        service.publish(7, True)
    youtube.videos().update.assert_not_called()
    service.publish(7, True, thumbnail_review_confirmed=True)
    assert service.status(7)['state'] == 'SCHEDULED'


def test_session_url_is_never_returned_and_ambiguous_restart_is_blocked(service, monkeypatch):
    job = {'movie_id': 7, 'title': 'Review', 'state': 'UPLOAD_ERROR', 'progress': 20,
           'upload_started': True, 'session_uri': 'private-session-url', 'snapshot': 'private-file', 'request_body': {}}
    service._save(job)
    public = service.status(7)
    assert public['can_resume']
    assert 'session_uri' not in public and 'snapshot' not in public and 'request_body' not in public
    job.pop('session_uri')
    service._save(job)
    with pytest.raises(ValueError, match='uncertain'):
        service.resume(7)


def test_different_channel_cannot_publish(service, monkeypatch):
    uploaded(service, channel_id='other-channel')
    youtube_status(service, monkeypatch)
    with pytest.raises(ValueError, match='channel match'):
        service.publish(7, True)


def test_missing_custom_thumbnail_confirmation_requires_manual_review(service, monkeypatch):
    uploaded(service)
    youtube_status(service, monkeypatch, details={'hasCustomThumbnail': False})
    job = service.refresh(7)
    assert job['thumbnail_state'] == 'needs_verification'
    with pytest.raises(ValueError, match='Thumbnail retry/Studio'):
        service.publish(7, True)


def test_music_attribution_is_kept_when_description_is_edited(service, monkeypatch, tmp_path):
    source = tmp_path / 'export.mp4'
    source.write_bytes(b'video')
    monkeypatch.setattr(service, '_movie_file', lambda _: ({'bgm_data_json': {'enabled': True, 'attribution': 'Required music credit'}}, source))
    monkeypatch.setattr(service, 'preflight', lambda _: {'ready': True})
    monkeypatch.setattr(service, 'account', lambda: {'is_authenticated': True})
    monkeypatch.setattr(service, '_launch', lambda _: None)
    service.start(7, {'title': 'Review', 'description': 'Edited description', 'made_for_kids': False})
    assert 'Required music credit' in service._load(7)['request_body']['snippet']['description']


def test_youtube_forced_private_response_is_not_reported_as_published(service, monkeypatch):
    uploaded(service)
    youtube = youtube_status(service, monkeypatch)
    youtube.videos().update().execute.side_effect = None
    youtube.videos().update().execute.return_value = {'status': {'privacyStatus': 'private'}}
    result = service.publish(7, True, thumbnail_review_confirmed=True)
    assert result['state'] == 'PRIVATE_REVIEW'
    assert 'did not confirm' in result['error']


def test_actual_end_frame_is_used_and_thumbnail_failure_preserves_video_id(service, monkeypatch, tmp_path):
    ffmpeg = shutil.which('ffmpeg')
    if not ffmpeg or not shutil.which('ffprobe'):
        pytest.skip('FFmpeg unavailable')
    source = tmp_path / 'review.mp4'
    subprocess.run([ffmpeg, '-v', 'error', '-f', 'lavfi', '-i', 'color=c=red:s=64x96:d=1',
        '-f', 'lavfi', '-i', 'color=c=blue:s=64x96:d=2', '-filter_complex', '[0:v][1:v]concat=n=2:v=1:a=0',
        '-c:v', 'libx264', '-pix_fmt', 'yuv420p', str(source)], check=True, timeout=30)
    service.repository.get_by_id.return_value = {'id': 7, 'status': 'COMPLETED', 'final_video_path': str(source), 'thumbnail_data_json': {'video_end_card': {'path': 'ending.jpg'}}}
    youtube = youtube_status(service, monkeypatch)
    youtube.channels().list().execute.return_value = {'items': [{'id': 'channel1', 'snippet': {'title': 'My Channel'}}]}
    upload = youtube.videos().insert.return_value
    upload.resumable_uri = 'sensitive-session'
    upload.next_chunk.return_value = (None, {'id': 'video123'})
    youtube.thumbnails().set().execute.side_effect = RuntimeError('Thumbnail permission unavailable')
    monkeypatch.setattr(service, '_launch', lambda _: None)
    service.start(7, {'title': 'Review', 'tags': [], 'made_for_kids': False})
    service._upload(7)
    result = service.status(7)
    assert result['video_id'] == 'video123'
    assert result['thumbnail_state'] == 'needs_attention'
    with Image.open(service._directory(7) / 'thumbnail.jpg') as frame:
        red, green, blue = frame.getpixel((32, 48))
        assert blue > 200 and red < 30
    body = youtube.videos().insert.call_args.kwargs['body']
    assert body['status']['privacyStatus'] == 'private'
    service.start(7, {'title': 'Review'})
    assert youtube.videos().insert.call_count == 1


@pytest.mark.parametrize('payload', [
    {'title': ''}, {'title': 'x' * 101}, {'title': '<invalid>'},
    {'title': 'Good', 'tags': ['x' * 501]},
])
def test_invalid_metadata_is_rejected(payload):
    with pytest.raises(ValueError):
        YouTubeUploadService.metadata(payload)
