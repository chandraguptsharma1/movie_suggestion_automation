import json
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest

from app.services.youtube_schedule_service import channel_schedule, next_slot, parse_time
from app.services.youtube_upload_service import YouTubeUploadService


@pytest.mark.parametrize('current,occupied,expected', [
    ('2026-10-24T12:59:00Z', [], '2026-10-24T18:30:00+05:30'),
    ('2026-10-24T13:00:00Z', [], '2026-10-25T18:30:00+05:30'),
    ('2026-10-24T14:00:00Z', [], '2026-10-25T18:30:00+05:30'),
    ('2026-10-24T10:00:00Z', ['2026-10-24T00:10:00Z'], '2026-10-25T18:30:00+05:30'),
    ('2026-10-24T10:00:00Z', ['2026-10-29T13:00:00Z'], '2026-10-30T18:30:00+05:30'),
    # UTC date is still the 24th but the occupied video's India date is the 25th.
    ('2026-10-24T10:00:00Z', ['2026-10-24T20:00:00Z'], '2026-10-26T18:30:00+05:30'),
    ('2026-12-31T10:00:00Z', ['2026-12-31T13:00:00Z'], '2027-01-01T18:30:00+05:30'),
])
def test_next_daily_1830_slot(current, occupied, expected):
    assert next_slot([parse_time(value) for value in occupied], parse_time(current)).isoformat() == expected


def channel():
    youtube = Mock()
    youtube.channels().list().execute.return_value = {'items': [
        {'id': 'channel1', 'contentDetails': {'relatedPlaylists': {'uploads': 'uploads1'}}}]}
    return youtube


def test_reads_all_pages_and_prefers_scheduled_date_over_upload_date(tmp_path):
    youtube = channel()
    youtube.playlistItems().list().execute.side_effect = [
        {'items': [{'contentDetails': {'videoId': 'current'}}, {'contentDetails': {'videoId': 'old'}}], 'nextPageToken': 'page2'},
        {'items': [{'contentDetails': {'videoId': 'future'}}]},
    ]
    youtube.videos().list().execute.side_effect = [
        {'items': [{'snippet': {'channelId': 'channel1', 'publishedAt': '2026-10-24T10:00:00Z'}, 'status': {'privacyStatus': 'public'}}]},
        {'items': [{'snippet': {'channelId': 'channel1', 'publishedAt': '2026-10-24T10:00:00Z'}, 'status': {'privacyStatus': 'private', 'publishAt': '2026-10-28T13:00:00Z'}}]},
    ]
    plan = channel_schedule(youtube, {'channel_id': 'channel1', 'video_id': 'current'}, tmp_path, parse_time('2026-10-24T09:00:00Z'))
    assert plan['publish_at_ist'] == '2026-10-29T18:30:00+05:30'
    assert plan['checked_videos'] == 2
    calls = youtube.videos().list.call_args_list
    assert calls[-2].kwargs['id'] == 'old'
    assert calls[-1].kwargs['id'] == 'future'
    assert youtube.playlistItems().list.call_args.kwargs['pageToken'] == 'page2'


def test_local_reservation_covers_remote_indexing_delay_and_retry_is_stable(tmp_path):
    youtube = channel()
    youtube.playlistItems().list().execute.return_value = {'items': []}
    directory = tmp_path / '9'
    directory.mkdir()
    (directory / 'job.json').write_text(json.dumps({'channel_id': 'channel1', 'video_id': 'other', 'state': 'SCHEDULED', 'publish_at': '2026-10-30T13:00:00Z'}))
    job = {'channel_id': 'channel1', 'video_id': 'current'}
    current = parse_time('2026-10-24T09:00:00Z')
    assert channel_schedule(youtube, job, tmp_path, current)['publish_at_ist'] == '2026-10-31T18:30:00+05:30'
    job.update(state='SCHEDULED', publish_at='2026-10-25T13:00:00Z')
    assert channel_schedule(youtube, job, tmp_path, current)['publish_at_ist'] == '2026-10-25T18:30:00+05:30'


def test_queue_failure_never_falls_back_to_guessed_date(tmp_path):
    youtube = channel()
    youtube.playlistItems().list().execute.side_effect = RuntimeError('YouTube unavailable')
    with pytest.raises(RuntimeError):
        channel_schedule(youtube, {'channel_id': 'channel1', 'video_id': 'current'}, tmp_path)
    youtube.videos().update.assert_not_called()
