"""Private-first YouTube uploads with an explicit Studio copyright review gate."""
import json
import logging
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload, build_http
from PIL import Image

from app.config import BACKEND_ROOT, settings
from app.database import project_repo
from app.services.youtube_oauth_service import youtube_oauth_service
from app.services.youtube_schedule_service import channel_schedule, parse_time

logger = logging.getLogger(__name__)


def now():
    return datetime.now(timezone.utc).isoformat()


def record(value):
    return value if isinstance(value, dict) else {}


class YouTubeUploadService:
    def __init__(self, root=None, repository=None):
        self.root = Path(root or settings.youtube_private_dir / 'uploads')
        self.repository = repository or project_repo
        self._locks = {}
        self._guard = threading.Lock()
        self._running = set()
        self._schedule_guard = threading.RLock()

    def _lock(self, movie_id):
        with self._guard:
            return self._locks.setdefault(movie_id, threading.RLock())

    def _directory(self, movie_id):
        path = self.root / str(int(movie_id))
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _load(self, movie_id):
        path = self._directory(movie_id) / 'job.json'
        return json.loads(path.read_text('utf-8')) if path.exists() else None

    def _save(self, job):
        # Upload workers and polling requests share a per-movie lock.
        with self._lock(job['movie_id']):
            job['updated_at'] = now()
            path = self._directory(job['movie_id']) / 'job.json'
            temp = path.with_suffix('.tmp')
            temp.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding='utf-8')
            temp.replace(path)

    def _public(self, job):
        if not job:
            return None
        result = {k: v for k, v in job.items() if k not in ('session_uri', 'snapshot', 'source_path', 'request_body', 'thumbnail_source_path')}
        result['running'] = job['movie_id'] in self._running
        result['can_resume'] = not job.get('video_id') and not result['running'] and (
            bool(job.get('session_uri')) or not job.get('upload_started'))
        result['copyright_check'] = ('reviewed_in_studio_by_agent' if job.get('studio_review_source') == 'agent' else
            'reviewed_in_studio_by_user' if job.get('studio_review_confirmed_at') else 'studio_review_required')
        result['thumbnail_url'] = f"/youtube-upload/{job['movie_id']}/thumbnail"
        result['thumbnail_display_confirmation_required'] = not bool(job.get('thumbnail_review_confirmed_at'))
        if job.get('video_id'):
            result['youtube_url'] = f"https://www.youtube.com/watch?v={job['video_id']}"
            result['studio_url'] = f"https://studio.youtube.com/video/{job['video_id']}/edit"
        return result

    def status(self, movie_id):
        with self._lock(movie_id):
            return self._public(self._load(movie_id))

    def _youtube(self):
        creds = youtube_oauth_service.get_credentials()
        if not creds:
            raise ValueError('YouTube account connect karein: Upload tab > Connect YouTube.')
        import google_auth_httplib2
        # Google's transport excludes 308 from redirects: during resumable
        # uploads it means "Resume Incomplete", including the server offset.
        transport = build_http()
        transport.timeout = 60
        return build('youtube', 'v3', http=google_auth_httplib2.AuthorizedHttp(
            creds, http=transport), cache_discovery=False)

    def account(self):
        configured = youtube_oauth_service.client_secret_path.exists()
        try:
            channels = self._youtube().channels().list(part='snippet', mine=True).execute().get('items', [])
            if not channels:
                raise ValueError('Connected account par YouTube channel nahi mila.')
            return {'client_secret_present': configured, 'is_authenticated': True,
                    'channel_title': channels[0]['snippet']['title']}
        except Exception as exc:
            message = self._error_message(exc)
            if 'invalid_grant' in message:
                message = 'YouTube authorization expire/revoke ho gaya hai. Upload tab se channel dobara connect karein.'
            return {'client_secret_present': configured, 'is_authenticated': False, 'error': message}

    def _movie_file(self, movie_id):
        movie = self.repository.get_by_id(int(movie_id))
        if not movie:
            raise ValueError('Movie/project nahi mila.')
        if movie.get('status') != 'COMPLETED':
            raise ValueError('Pehle Shorts export complete karein.')
        raw = movie.get('final_video_path')
        if not raw:
            raise ValueError('Exported Shorts file nahi mili. Video dobara export karein.')
        path = Path(str(raw))
        if not path.is_absolute():
            path = BACKEND_ROOT / path
        if not path.is_file():
            raise ValueError('Local exported video missing hai. Shorts dobara export karein.')
        return movie, path

    def _probe(self, path):
        result = subprocess.run([settings.ffprobe_binary or 'ffprobe', '-v', 'error',
            '-show_streams', '-show_format', '-of', 'json', str(path)],
            capture_output=True, text=True, check=True, timeout=30)
        data = json.loads(result.stdout)
        video = next((s for s in data.get('streams', []) if s.get('codec_type') == 'video'), None)
        duration = float(record(data.get('format')).get('duration') or 0)
        if not video or duration <= 0:
            raise ValueError('Video playable nahi hai ya duration invalid hai.')
        return {'duration_seconds': duration, 'width': int(video['width']), 'height': int(video['height']),
                'has_audio': any(s.get('codec_type') == 'audio' for s in data.get('streams', [])),
                'size_bytes': path.stat().st_size}

    def preflight(self, movie_id):
        movie, path = self._movie_file(movie_id)
        media = self._probe(path)
        warnings = [
            'Movie/trailer footage aur music par Content ID claim aa sakta hai. Local file check copyright clearance nahi hai.',
            'YouTube Studio mein Checks/Copyright review zaroori hai. Claims baad mein bhi aa sakte hain.',
        ]
        if media['width'] > media['height'] or media['duration_seconds'] > 180:
            warnings.append('Video Shorts format (square/vertical, maximum 3 minutes) mein nahi lagta.')
        if not media['has_audio']:
            warnings.append('Video mein audio stream nahi hai.')
        card = record(record(movie.get('thumbnail_data_json')).get('video_end_card'))
        if not card.get('path'):
            raise ValueError('Ending thumbnail missing hai. Video dobara compose karein, taaki last 2 seconds mein thumbnail ho.')
        if movie.get('thumbnail_path') and Path(card['path']).resolve() != Path(movie['thumbnail_path']).resolve():
            raise ValueError('Thumbnail design change hua hai. Thumbnail Studio mein Update video ending click karein, phir upload karein.')
        return {'ready': True, 'media': media, 'warnings': warnings,
                'copyright_check': 'not_available_before_upload', 'privacy': 'private'}

    @staticmethod
    def metadata(payload):
        title = str(payload.get('title') or '').strip()
        description = str(payload.get('description') or '').strip()
        if not title or len(title) > 100 or any(c in title for c in '<>'):
            raise ValueError('Title 1–100 characters ka ho; < aur > allowed nahi hain.')
        if len(description.encode('utf-8')) > 5000 or any(c in description for c in '<>'):
            raise ValueError('Description 5000 UTF-8 bytes ke andar ho; < aur > allowed nahi hain.')
        tags = list(dict.fromkeys(str(t).strip() for t in payload.get('tags', []) if str(t).strip()))
        cost = sum(len(t) + (2 if ' ' in t else 0) for t in tags) + max(0, len(tags) - 1)
        if cost > 500 or any('<' in t or '>' in t for t in tags):
            raise ValueError('Tags ka total YouTube limit 500 characters se zyada hai ya invalid tag hai.')
        category = str(payload.get('category_id') or '1')
        if not category.isdigit():
            raise ValueError('Valid YouTube category choose karein.')
        return {'snippet': {'title': title, 'description': description, 'tags': tags, 'categoryId': category},
                'status': {'privacyStatus': 'private', 'selfDeclaredMadeForKids': bool(payload.get('made_for_kids', False))}}

    def start(self, movie_id, payload):
        with self._lock(movie_id):
            previous = self._load(movie_id)
            if previous:
                return self._public(previous)
            project, path = self._movie_file(movie_id)
            payload = dict(payload)
            music = project.get('bgm_data_json') or {}
            credit = music.get('attribution') if music.get('enabled') else ''
            if credit and credit not in (payload.get('description') or ''):
                payload['description'] = (payload.get('description') or '').rstrip() + '\n\nMusic credit:\n' + credit
            body = self.metadata(payload)
            self.preflight(movie_id)
            account = self.account()
            if not account['is_authenticated']:
                raise ValueError(account.get('error') or 'YouTube account dobara connect karein.')
            job = {'movie_id': movie_id, 'state': 'PREPARING', 'progress': 0, 'created_at': now(),
                   'title': body['snippet']['title'], 'request_body': body, 'snapshot': str(path), 'source_path': str(path),
                   'thumbnail_state': 'pending', 'upload_started': False, 'error': None}
            self._save(job)
            self._launch(movie_id)
            return self._public(job)

    def resume(self, movie_id):
        with self._lock(movie_id):
            job = self._load(movie_id)
            if not job:
                raise ValueError('Upload job nahi mila.')
            if movie_id in self._running or job.get('video_id'):
                return self._public(job)
            if job.get('upload_started') and not job.get('session_uri'):
                raise ValueError('Pehle upload ka result uncertain hai. YouTube Studio check karein; duplicate upload automatically start nahi kiya jayega.')
            job['state'] = 'UPLOADING' if job.get('upload_started') else 'PREPARING'
            job['error'] = None
            self._save(job)
            self._launch(movie_id)
            return self._public(job)

    def _launch(self, movie_id):
        self._running.add(movie_id)
        threading.Thread(target=self._upload, args=(movie_id,), name=f'youtube-upload-{movie_id}', daemon=True).start()

    def _upload(self, movie_id):
        with self._lock(movie_id):
            job = self._load(movie_id)
        try:
            youtube = self._youtube()
            if not job.get('upload_started'):
                source = Path(job.get('source_path') or job['snapshot'])
                snapshot = self._directory(movie_id) / 'upload.mp4'
                if source != snapshot:
                    shutil.copyfile(source, snapshot)
                job['snapshot'] = str(snapshot)
                job['media'] = self._probe(snapshot)
                frame = self._directory(movie_id) / 'thumbnail.jpg'
                subprocess.run([settings.ffmpeg_binary or 'ffmpeg', '-v', 'error', '-y',
                    '-ss', str(max(0, job['media']['duration_seconds'] - 0.8)), '-i', str(snapshot),
                    '-frames:v', '1', '-q:v', '2', str(frame)], capture_output=True, check=True, timeout=60)
                with Image.open(frame) as image:
                    image = image.convert('RGB')
                    image.thumbnail((1920, 1920))
                    image.save(frame, 'JPEG', quality=88)
                channels = youtube.channels().list(part='snippet', mine=True).execute().get('items', [])
                if not channels:
                    raise ValueError('Connected Google account par YouTube channel nahi mila.')
                job['channel_id'] = channels[0]['id']
                job['channel_title'] = channels[0]['snippet']['title']
                job['state'] = 'UPLOADING'
                job['upload_started'] = True
                self._save(job)
            else:
                channels = youtube.channels().list(part='id', mine=True).execute().get('items', [])
                if not any(c['id'] == job['channel_id'] for c in channels):
                    raise ValueError('Resume ke liye original YouTube channel connect karein.')
            media = MediaFileUpload(job['snapshot'], mimetype='video/mp4', chunksize=8 * 1024 * 1024, resumable=True)
            request = youtube.videos().insert(part='snippet,status', body=job['request_body'], media_body=media, notifySubscribers=False)
            if job.get('session_uri'):
                request.resumable_uri = job['session_uri']
                request.resumable_progress = 0
                request._in_error_state = True
            response = None
            while response is None:
                try:
                    progress, response = request.next_chunk(num_retries=3)
                finally:
                    if request.resumable_uri:
                        job['session_uri'] = request.resumable_uri
                    self._save(job)
                if progress:
                    job['progress'] = int(progress.progress() * 100)
                    self._save(job)
            job['video_id'] = response['id']
            job['state'] = 'PRIVATE_REVIEW'
            job['progress'] = 100
            job['error'] = None
            self._save(job)
            self._set_thumbnail(youtube, job)
            self._refresh(youtube, job)
        except Exception as exc:
            logger.warning('YouTube upload failed for movie %s: %s', movie_id, self._error_message(exc))
            job['state'] = 'PRIVATE_REVIEW' if job.get('video_id') else 'UPLOAD_ERROR'
            job['error'] = self._error_message(exc)
            self._save(job)
        finally:
            with self._lock(movie_id):
                self._running.discard(movie_id)

    @staticmethod
    def _error_message(exc):
        if hasattr(exc, 'content'):
            status = getattr(getattr(exc, 'resp', None), 'status', None)
            prefix = f'YouTube API HTTP {status}' if status else 'YouTube API request failed'
            try:
                error = json.loads(exc.content).get('error', {})
                message = error.get('message')
                reasons = ', '.join(str(item['reason']) for item in error.get('errors', []) if item.get('reason'))
                detail = f'{message or "Request failed"}' + (f' ({reasons})' if reasons else '')
                return f'{prefix}: {detail}'[:800]
            except (ValueError, TypeError, AttributeError):
                # Do not expose raw HTML, upload session URLs or auth headers.
                return f'{prefix}: server returned a non-JSON error response.'
        return str(exc)[:800]

    def _set_thumbnail(self, youtube, job):
        try:
            youtube.thumbnails().set(videoId=job['video_id'], media_body=MediaFileUpload(
                str(self._directory(job['movie_id']) / 'thumbnail.jpg'), mimetype='image/jpeg')).execute()
            job['thumbnail_state'] = 'accepted_by_youtube'
            job['thumbnail_error'] = None
            job['thumbnail_updated_at'] = now()
            job.pop('thumbnail_review_confirmed_at', None)
        except Exception as exc:
            job['thumbnail_state'] = 'needs_attention'
            job['thumbnail_error'] = self._error_message(exc) + ' Studio mein channel eligibility aur Shorts thumbnail verify karein.'
        self._save(job)

    def retry_thumbnail(self, movie_id):
        with self._lock(movie_id):
            job = self._require_uploaded(movie_id)
            if movie_id in self._running:
                raise ValueError('Upload processing chal rahi hai. Thoda wait karein.')
            youtube = self._youtube()
            # Check account ownership before changing an existing remote video.
            self._refresh(youtube, job)
            project = self.repository.get_by_id(int(movie_id))
            source = project.get('thumbnail_path') if isinstance(project, dict) else None
            if source and Path(source).is_file():
                frame = self._directory(movie_id) / 'thumbnail.jpg'
                temp = frame.with_suffix('.tmp.jpg')
                with Image.open(source) as image:
                    image = image.convert('RGB')
                    image.thumbnail((1920, 1920))
                    image.save(temp, 'JPEG', quality=95)
                temp.replace(frame)
                job['thumbnail_source'] = 'latest_project_design'
                job['thumbnail_source_path'] = source
                job['uploaded_video_ending_unchanged'] = True
            self._set_thumbnail(youtube, job)
            self._refresh(youtube, job)
            return self._public(job)

    def _require_uploaded(self, movie_id):
        job = self._load(movie_id)
        if not job or not job.get('video_id'):
            raise ValueError('Pehle private upload complete karein.')
        return job

    def _refresh(self, youtube, job):
        items = youtube.videos().list(part='snippet,status,processingDetails,contentDetails', id=job['video_id']).execute().get('items', [])
        if not items:
            raise ValueError('Uploaded video connected account se access nahi ho raha. Channel aur Studio check karein.')
        item = items[0]
        if item.get('snippet', {}).get('channelId') != job.get('channel_id'):
            raise ValueError('YouTube channel match nahi karta. Original channel connect karein.')
        status = item.get('status', {})
        processing = item.get('processingDetails', {})
        region = item.get('contentDetails', {}).get('regionRestriction', {})
        blocked = (status.get('uploadStatus') in ('rejected', 'failed', 'deleted')
                   or processing.get('processingStatus') in ('failed', 'terminated')
                   or bool(status.get('rejectionReason')) or bool(status.get('failureReason'))
                   or bool(region.get('blocked')) or 'allowed' in region)
        job['youtube_status'] = {'privacy': status.get('privacyStatus'), 'upload_status': status.get('uploadStatus'),
            'processing_status': processing.get('processingStatus'), 'rejection_reason': status.get('rejectionReason'),
            'failure_reason': status.get('failureReason'), 'region_restriction': region}
        job['status_fields'] = {key: status[key] for key in (
            'license', 'embeddable', 'publicStatsViewable', 'selfDeclaredMadeForKids', 'containsSyntheticMedia'
        ) if key in status}
        job['restriction_detected'] = blocked
        job['processed'] = status.get('uploadStatus') == 'processed' and processing.get('processingStatus') == 'succeeded'
        custom_thumbnail = item.get('contentDetails', {}).get('hasCustomThumbnail')
        thumbnails = item.get('snippet', {}).get('thumbnails', {})
        for size in ('maxres', 'standard', 'high', 'medium', 'default'):
            if thumbnails.get(size, {}).get('url'):
                job['youtube_thumbnail_url'] = thumbnails[size]['url']
                break
        job['youtube_status']['custom_thumbnail'] = custom_thumbnail
        if custom_thumbnail is False and job['processed'] and job.get('thumbnail_state') == 'accepted_by_youtube':
            job['thumbnail_state'] = 'needs_verification'
            job['thumbnail_error'] = 'Thumbnail API accepted the image, but YouTube has not confirmed a custom thumbnail. Verify/set the ending image in Studio.'
        elif custom_thumbnail is True and job.get('thumbnail_state') == 'needs_verification':
            job['thumbnail_state'] = 'accepted_by_youtube'
            job['thumbnail_error'] = None
        job['checked_at'] = now()
        job['publish_at'] = status.get('publishAt')
        job['state'] = ('RESTRICTION_DETECTED' if blocked else
            'PUBLISHED' if status.get('privacyStatus') == 'public' else
            'SCHEDULED' if status.get('publishAt') else 'PRIVATE_REVIEW')
        self._save(job)
        return self._public(job)

    def refresh(self, movie_id):
        with self._lock(movie_id):
            job = self._require_uploaded(movie_id)
            if movie_id in self._running:
                return self._public(job)
            return self._refresh(self._youtube(), job)

    def publish(self, movie_id, studio_review_confirmed, publish_at=None, thumbnail_review_confirmed=False):
        with self._lock(movie_id), self._schedule_guard:
            job = self._require_uploaded(movie_id)
            if movie_id in self._running:
                raise ValueError('Upload complete hone ka wait karein.')
            if not studio_review_confirmed:
                raise ValueError('YouTube Studio ke Checks/Copyright results pehle review aur confirm karein.')
            youtube = self._youtube()
            self._refresh(youtube, job)
            if job.get('restriction_detected') or not job.get('processed'):
                raise ValueError('Processing incomplete hai ya restriction detect hui. Studio check karein.')
            if not thumbnail_review_confirmed:
                raise ValueError('Thumbnail retry/Studio preview check karke displayed Shorts thumbnail confirm karein. API acceptance display confirmation nahi hai.')
            if job['state'] == 'PUBLISHED':
                raise ValueError('Video already public hai; existing public video ko reschedule nahi kiya jayega.')
            if publish_at is not None:
                raise ValueError('Manual schedule disabled hai. Next available date par 6:30 PM IST automatically choose hoga.')
            plan = channel_schedule(youtube, job, self.root)
            if job['state'] == 'SCHEDULED' and job.get('publish_at') and parse_time(job['publish_at']) == parse_time(plan['publish_at']):
                return self._public(job)
            status = {**job.get('status_fields', {}), 'privacyStatus': 'private', 'publishAt': plan['publish_at']}
            response = youtube.videos().update(part='status', body={'id': job['video_id'], 'status': status}).execute()
            actual = response.get('status', {})
            if (actual.get('privacyStatus') != 'private' or not actual.get('publishAt')
                    or parse_time(actual['publishAt']) != parse_time(plan['publish_at'])):
                job['state'] = 'PRIVATE_REVIEW'
                job['error'] = 'YouTube did not confirm the requested publication/schedule. Check Studio and API-project eligibility before retrying.'
                self._save(job)
                return self._public(job)
            job['state'] = 'SCHEDULED'
            job['schedule_plan'] = plan
            job['studio_review_confirmed_at'] = now()
            job['thumbnail_review_confirmed_at'] = now()
            job['publish_at'] = status.get('publishAt')
            job['error'] = None
            self._save(job)
            return self._public(job)

    def schedule_preview(self, movie_id):
        with self._lock(movie_id), self._schedule_guard:
            job = self._require_uploaded(movie_id)
            if movie_id in self._running:
                raise ValueError('Upload complete hone ka wait karein.')
            youtube = self._youtube()
            self._refresh(youtube, job)
            if job['state'] == 'PUBLISHED':
                raise ValueError('Video already public hai.')
            return channel_schedule(youtube, job, self.root)

    def mark_agent_review(self, movie_id, evidence):
        with self._lock(movie_id):
            job = self._require_uploaded(movie_id)
            job['studio_review_source'] = 'agent'
            job['studio_review_evidence'] = evidence
            self._save(job)

    def hold_scheduled(self, movie_id):
        """Cancel a future release if a monitored restriction/claim appears."""
        with self._lock(movie_id), self._schedule_guard:
            job = self._require_uploaded(movie_id)
            youtube = self._youtube()
            self._refresh(youtube, job)
            if not job.get('publish_at') or job.get('youtube_status', {}).get('privacy') != 'private':
                return self._public(job)
            status = {**job.get('status_fields', {}), 'privacyStatus': 'private'}
            status.pop('publishAt', None)
            response = youtube.videos().update(part='status', body={'id': job['video_id'], 'status': status}).execute()
            actual = response.get('status', {})
            if actual.get('publishAt') or actual.get('privacyStatus') != 'private':
                raise ValueError('YouTube did not confirm cancellation of the scheduled release.')
            job['state'] = 'PRIVATE_REVIEW'
            job['publish_at'] = None
            job['automation_hold'] = True
            self._save(job)
            return self._public(job)


youtube_upload_service = YouTubeUploadService()
