"""Durable private-upload queue. Studio evidence, never empty API restrictions, gates release."""
import json
import logging
import os
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone

from app.database import DB_PATH, project_repo
from app.services.youtube_upload_service import youtube_upload_service

logger = logging.getLogger(__name__)


class PublishingAutomation:
    def __init__(self, db_path=None, repository=None, uploader=None, clock=None):
        self.db_path = db_path or DB_PATH
        self.repository = repository or project_repo
        self.uploader = uploader or youtube_upload_service
        self.clock = clock or (lambda: datetime.now(timezone.utc).timestamp())
        self.guard = threading.RLock()
        self.thread = None
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS publishing_automation (
                project_id INTEGER PRIMARY KEY, payload TEXT NOT NULL, state TEXT NOT NULL,
                next_check REAL NOT NULL DEFAULT 0, attempts INTEGER NOT NULL DEFAULT 0,
                message TEXT NOT NULL DEFAULT '', evidence TEXT, updated_at REAL NOT NULL)''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(str(self.db_path), timeout=20)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def list(self):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM publishing_automation ORDER BY project_id').fetchall()
        return [self.public(dict(row)) for row in rows]

    def get(self, project_id):
        with self.connect() as db:
            row = db.execute('SELECT * FROM publishing_automation WHERE project_id=?', (project_id,)).fetchone()
        return self.public(dict(row)) if row else None

    @staticmethod
    def public(row):
        row.pop('payload', None)
        row['evidence'] = json.loads(row['evidence']) if row.get('evidence') else None
        return row

    def update(self, pid, state, message, delay=120, evidence=None):
        with self.connect() as db:
            db.execute('''UPDATE publishing_automation SET state=?,message=?,next_check=?,
                attempts=attempts+1,updated_at=?,evidence=COALESCE(?,evidence) WHERE project_id=?''',
                (state, message, self.clock() + delay, self.clock(),
                 json.dumps(evidence) if evidence is not None else None, pid))

    def enable(self, pid, payload=None):
        project = self.repository.get_by_id(pid)
        if not project:
            raise ValueError('Project not found.')
        if len(project.get('movies_json') or []) != 1:
            raise ValueError('Automatic publishing currently supports single-movie reviews.')
        script = project.get('script_data_json') or {}
        title = str(script.get('youtube_title') or project['movies_json'][0]['title'] + ' | Hindi Movie Review #Shorts')
        defaults = {'title': title[:100], 'description': script.get('youtube_description') or
                    f"Cinematic Hindi movie review of {project['movies_json'][0]['title']}.\n#Shorts #MovieReview",
                    'tags': script.get('tags') or script.get('youtube_tags') or ['Shorts', 'Movie Review', 'Hindi Review'],
                    'category_id': '24', 'made_for_kids': False}
        body = self.uploader.metadata(payload or defaults)
        # Store a validated request, with the channel's review audience/category defaults.
        normalized = {'title': body['snippet']['title'], 'description': body['snippet']['description'],
                      'tags': body['snippet']['tags'], 'category_id': body['snippet']['categoryId'],
                      'made_for_kids': body['status']['selfDeclaredMadeForKids']}
        with self.connect() as db:
            db.execute('''INSERT OR IGNORE INTO publishing_automation
                (project_id,payload,state,next_check,updated_at) VALUES(?,?,'QUEUED',0,?)''',
                (pid, json.dumps(normalized, ensure_ascii=False), self.clock()))
        return self.get(pid)

    def record_studio_evidence(self, pid, evidence):
        """Called by the UI-review agent after observing this exact video in Studio."""
        with self.guard:
            row = self.get(pid)
            job = self.uploader.status(pid)
            if not row or not job or not job.get('video_id'):
                raise ValueError('Automatic upload must complete before Studio review.')
            if evidence['video_id'] != job['video_id']:
                raise ValueError('Studio evidence belongs to a different video.')
            stamp = datetime.fromisoformat(evidence['observed_at'].replace('Z', '+00:00'))
            if stamp.tzinfo is None or not -30 <= self.clock() - stamp.timestamp() <= 600:
                raise ValueError('Fresh timezone-aware Studio evidence (within 10 minutes) is required.')
            if not evidence.get('details', '').strip():
                raise ValueError('Record the actual visible Studio checks result and thumbnail observation.')
            evidence = {**evidence, 'thumbnail_updated_at': job.get('thumbnail_updated_at')}
            blocked = evidence['copyright_status'] in ('claim', 'blocked')
            self.update(pid, 'WAITING_STUDIO',
                        'Studio found a copyright claim/block; video held privately.' if blocked else
                        'Studio observation saved; automatic scheduling checks pending.',
                        delay=0, evidence=evidence)
            return self.get(pid)

    def tick(self, pid):
        with self.guard:
            row = self.get(pid)
            if not row or row['state'] == 'HELD' or row['next_check'] > self.clock():
                return
            try:
                job = self.uploader.status(pid)
                if (row.get('evidence') or {}).get('copyright_status') in ('claim', 'blocked'):
                    self.uploader.hold_scheduled(pid)
                    self.update(pid, 'HELD', 'Studio found a copyright claim/block. Scheduled release cancelled; video held privately.', 900)
                    return
                if not job:
                    if any(other['project_id'] != pid and
                           (self.uploader.status(other['project_id']) or {}).get('running') for other in self.list()):
                        self.update(pid, 'QUEUED', 'Waiting for the previous private upload to finish.', 30)
                        return
                    project = self.repository.get_by_id(pid)
                    if not project or project.get('status') != 'COMPLETED':
                        self.update(pid, 'WAITING_VIDEO', 'Waiting for the finished video.', 30)
                        return
                    with self.connect() as db:
                        payload = json.loads(db.execute('SELECT payload FROM publishing_automation WHERE project_id=?', (pid,)).fetchone()[0])
                    job = self.uploader.start(pid, payload)
                if job.get('running'):
                    self.update(pid, 'UPLOADING', 'Private upload in progress; no duplicate upload will be created.', 30)
                    return
                if not job.get('video_id'):
                    if job.get('can_resume'):
                        self.uploader.resume(pid)
                        self.update(pid, 'UPLOADING', 'Resuming the existing private upload.', 120)
                    else:
                        self.update(pid, 'ATTENTION', 'Upload result uncertain; Studio inspection required to prevent a duplicate.', 900)
                    return
                job = self.uploader.refresh(pid)
                if job.get('restriction_detected'):
                    self.uploader.hold_scheduled(pid)
                    self.update(pid, 'HELD', 'YouTube restriction/block detected. Automatic scheduling stopped.', 900)
                    return
                if job['state'] == 'PUBLISHED':
                    self.update(pid, 'PUBLISHED', 'Published. Agent continues checking Studio for later claims.', 3600)
                    return
                if job['state'] == 'SCHEDULED':
                    self.update(pid, 'SCHEDULED', 'Scheduled at 6:30 PM IST. Agent continues checking Studio.', 900)
                    return
                if not job.get('processed'):
                    self.update(pid, 'PROCESSING', 'YouTube is processing the upload; automatic recheck pending.', 120)
                    return
                # Delay after upload so an immediate "processed" response is not used as clearance.
                evidence = row.get('evidence') or {}
                fresh = bool(evidence.get('observed_at')) and 0 <= self.clock() - datetime.fromisoformat(evidence['observed_at'].replace('Z', '+00:00')).timestamp() <= 600
                verified = (fresh and evidence.get('video_id') == job['video_id'] and
                    evidence.get('copyright_status') == 'clear' and evidence.get('checks_complete') is True and
                    evidence.get('thumbnail_matches') is True and
                    evidence.get('thumbnail_updated_at') == job.get('thumbnail_updated_at'))
                if not verified:
                    self.update(pid, 'WAITING_STUDIO', 'Waiting for the agent to verify completed Studio checks and the displayed Shorts thumbnail.', 120)
                    return
                result = self.uploader.publish(pid, True, thumbnail_review_confirmed=True)
                if result['state'] != 'SCHEDULED':
                    raise ValueError(result.get('error') or 'YouTube has not confirmed the schedule.')
                self.uploader.mark_agent_review(pid, evidence)
                self.update(pid, 'SCHEDULED', 'Verified in Studio and scheduled for the next available 6:30 PM IST slot.', 900)
            except Exception as exc:
                logger.warning('Publishing automation project %s: %s', pid, self.uploader._error_message(exc))
                self.update(pid, 'RETRY_PENDING', self.uploader._error_message(exc), min(900, 60 * 2 ** min(row['attempts'], 4)))

    def start_worker(self):
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._worker, name='publishing-automation', daemon=True)
        self.thread.start()

    def _worker(self):
        from pathlib import Path
        # Keep a single coordinator even when more than one server process is started.
        with Path(str(self.db_path) + '.publishing.lock').open('a+b') as lock:
            lock.write(b'0'); lock.flush()
            while True:
                try:
                    lock.seek(0)
                    if os.name == 'nt':
                        import msvcrt
                        msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        import fcntl
                        fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except OSError:
                    threading.Event().wait(10)
            while True:
                try:
                    for row in self.list():
                        self.tick(row['project_id'])
                except Exception:
                    logger.exception('Publishing coordinator will retry')
                threading.Event().wait(10)


publishing_automation = PublishingAutomation()
