"""Choose a channel's next daily 18:30 India-time release slot."""
import json
from datetime import datetime, time, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30), name='IST')


def parse_time(value):
    when = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if when.tzinfo is None:
        raise ValueError('YouTube schedule timestamp has no timezone')
    return when


def next_slot(occupied, current_time=None):
    current = (current_time or datetime.now(timezone.utc)).astimezone(IST)
    day = current.date()
    if datetime.combine(day, time(18, 30), IST) <= current:
        day += timedelta(days=1)
    if occupied:
        day = max(day, max(value.astimezone(IST).date() for value in occupied) + timedelta(days=1))
    return datetime.combine(day, time(18, 30), IST)


def channel_schedule(youtube, job, jobs_root, current_time=None):
    """Read all owner-visible uploads, including private/scheduled videos.

    Never guess a free slot if YouTube cannot return the channel queue.
    Local confirmed reservations cover YouTube's indexing delay.
    """
    channels = youtube.channels().list(part='contentDetails', mine=True).execute().get('items', [])
    channel = next((item for item in channels if item.get('id') == job['channel_id']), None)
    if not channel:
        raise ValueError('Original YouTube channel connect karein before scheduling.')
    playlist = channel.get('contentDetails', {}).get('relatedPlaylists', {}).get('uploads')
    if not playlist:
        raise ValueError('Channel uploads queue unavailable; schedule slot safely check nahi ho saka.')
    occupied, total, token, visited = [], 0, None, set()
    while True:
        args = {'part': 'contentDetails', 'playlistId': playlist, 'maxResults': 50}
        if token:
            args['pageToken'] = token
        page = youtube.playlistItems().list(**args).execute()
        ids = [item.get('contentDetails', {}).get('videoId') for item in page.get('items', [])]
        ids = [value for value in ids if value and value != job['video_id']]
        if ids:
            videos = youtube.videos().list(part='snippet,status', id=','.join(ids), maxResults=50).execute().get('items', [])
            for video in videos:
                if video.get('snippet', {}).get('channelId') != job['channel_id']:
                    continue
                status = video.get('status', {})
                if status.get('uploadStatus') in ('deleted', 'failed', 'rejected'):
                    continue
                stamp = status.get('publishAt') or video.get('snippet', {}).get('publishedAt')
                if not stamp:
                    raise ValueError('Channel video date missing; schedule queue verify karein.')
                occupied.append(parse_time(stamp))
                total += 1
        token = page.get('nextPageToken')
        if not token:
            break
        if token in visited:
            raise ValueError('YouTube queue pagination incomplete. Retry schedule check.')
        visited.add(token)
    for path in jobs_root.glob('*/job.json'):
        saved = json.loads(path.read_text(encoding='utf-8'))
        if (saved.get('channel_id') == job['channel_id'] and saved.get('video_id') != job['video_id']
                and saved.get('state') == 'SCHEDULED' and saved.get('publish_at')):
            occupied.append(parse_time(saved['publish_at']))
    current = current_time or datetime.now(timezone.utc)
    existing = job.get('publish_at') if job.get('state') == 'SCHEDULED' else None
    existing = parse_time(existing) if existing else None
    if existing and existing > current and existing.astimezone(IST).time() == time(18, 30):
        slot = existing.astimezone(IST)
    else:
        slot = next_slot(occupied, current)
    return {'publish_at': slot.astimezone(timezone.utc).isoformat(), 'publish_at_ist': slot.isoformat(),
            'timezone': 'Asia/Kolkata', 'daily_time': '18:30', 'checked_videos': total,
            'latest_occupied_date': max(occupied).astimezone(IST).date().isoformat() if occupied else None}
