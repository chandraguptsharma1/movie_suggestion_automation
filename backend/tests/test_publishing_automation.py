from datetime import datetime, timezone
from unittest.mock import Mock
import pytest
from app.services.publishing_automation_service import PublishingAutomation
from app.services.youtube_upload_service import YouTubeUploadService


@pytest.fixture
def auto(tmp_path):
    repo, uploader = Mock(), Mock()
    repo.get_by_id.return_value = {'status': 'COMPLETED', 'movies_json': [{'title': 'Review Movie'}], 'script_data_json': {}}
    uploader.metadata.side_effect = YouTubeUploadService.metadata
    uploader._error_message.side_effect = str
    uploader.status.return_value = {'video_id': 'abc', 'processed': True, 'state': 'PRIVATE_REVIEW', 'thumbnail_updated_at': 'v1'}
    uploader.refresh.side_effect = lambda _: uploader.status.return_value.copy()
    uploader.publish.return_value = {'state': 'SCHEDULED'}
    service = PublishingAutomation(tmp_path / 'auto.db', repo, uploader, lambda: 1000000)
    service.enable(1)
    return service


def evidence(**kwargs):
    return {'video_id': 'abc', 'observed_at': datetime.fromtimestamp(1000000, timezone.utc).isoformat(),
            'copyright_status': 'clear', 'checks_complete': True, 'thumbnail_matches': True,
            'details': 'Studio checks complete, no copyright issues; displayed cover matches poster.', **kwargs}


def test_private_upload_and_duplicate_enable_survive_restart(auto):
    auto.uploader.status.return_value = None
    auto.uploader.start.return_value = {'running': True}
    auto.tick(1)
    auto.enable(1)
    assert auto.get(1)['state'] == 'UPLOADING'
    auto.uploader.start.assert_called_once()
    restored = PublishingAutomation(auto.db_path, auto.repository, auto.uploader, auto.clock)
    restored.tick(1)
    auto.uploader.start.assert_called_once()


@pytest.mark.parametrize('changes', [{}, {'checks_complete': False}, {'thumbnail_matches': False}, {'copyright_status': 'pending'}])
def test_no_api_inference_or_incomplete_studio_clearance(auto, changes):
    if changes:
        auto.record_studio_evidence(1, evidence(**changes))
    auto.tick(1)
    assert auto.get(1)['state'] == 'WAITING_STUDIO'
    auto.uploader.publish.assert_not_called()


def test_verified_clear_video_schedules_and_records_agent_source(auto):
    auto.record_studio_evidence(1, evidence())
    auto.tick(1)
    auto.uploader.publish.assert_called_once_with(1, True, thumbnail_review_confirmed=True)
    auto.uploader.mark_agent_review.assert_called_once()
    assert auto.get(1)['state'] == 'SCHEDULED'


@pytest.mark.parametrize('change', [{'video_id': 'other'}, {'observed_at': '1970-01-01T00:00:00+00:00'}, {'observed_at': '2026-01-01T00:00:00'}])
def test_rejects_wrong_video_and_stale_evidence(auto, change):
    with pytest.raises(ValueError):
        auto.record_studio_evidence(1, evidence(**change))


def test_thumbnail_change_invalidates_prior_observation(auto):
    auto.record_studio_evidence(1, evidence())
    auto.uploader.status.return_value['thumbnail_updated_at'] = 'v2'
    auto.tick(1)
    auto.uploader.publish.assert_not_called()


def test_claim_cancels_schedule_and_failed_cancellation_retries(auto):
    auto.record_studio_evidence(1, evidence(copyright_status='claim'))
    auto.uploader.hold_scheduled.side_effect = RuntimeError('network temporarily down')
    auto.tick(1)
    assert auto.get(1)['state'] == 'RETRY_PENDING'
    auto.uploader.hold_scheduled.side_effect = None
    auto.clock = lambda: 1001000
    auto.tick(1)
    assert auto.get(1)['state'] == 'HELD'
    auto.uploader.publish.assert_not_called()


def test_processing_pending_and_remote_block_never_publish(auto):
    auto.record_studio_evidence(1, evidence())
    auto.uploader.status.return_value['processed'] = False
    auto.tick(1)
    assert auto.get(1)['state'] == 'PROCESSING'
    auto.clock = lambda: 1001000
    auto.uploader.status.return_value['restriction_detected'] = True
    auto.tick(1)
    assert auto.get(1)['state'] == 'HELD'
    auto.uploader.publish.assert_not_called()


def test_second_upload_waits_for_first(auto):
    auto.enable(2)
    auto.uploader.status.side_effect = lambda pid: {'running': True} if pid == 1 else None
    auto.tick(2)
    assert auto.get(2)['state'] == 'QUEUED'
    auto.uploader.start.assert_not_called()
