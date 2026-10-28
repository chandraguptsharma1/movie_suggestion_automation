"""Persistent FIFO, one cinematic movie at a time. Does not publish videos."""
import json
import logging
import os
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from app.database import DB_PATH, project_repo
from app.services.auto_pilot_service import auto_pilot_service

logger = logging.getLogger(__name__)


def now():
    return datetime.now(timezone.utc).isoformat()


class ProcessingQueue:
    def __init__(self, db_path=None, repository=None, processor=None, publisher=None):
        self.db_path = Path(db_path or DB_PATH)
        self.repository = repository or project_repo
        self.processor = processor or auto_pilot_service.run_auto_pilot
        self.publisher = publisher
        self.wake = threading.Event()
        self.guard = threading.Lock()
        self.thread = None
        with self.connect() as db:
            db.execute('''CREATE TABLE IF NOT EXISTS processing_queue (
                id INTEGER PRIMARY KEY AUTOINCREMENT, movie_key TEXT UNIQUE NOT NULL,
                movie_json TEXT NOT NULL, project_id INTEGER, state TEXT NOT NULL DEFAULT 'QUEUED',
                error TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL)''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(str(self.db_path), timeout=20)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    @staticmethod
    def key(movie):
        return f"{movie.get('media_type') or 'movie'}:{movie.get('tmdb_id') or (movie['title'].strip().casefold() + ':' + str(movie.get('year') or ''))}"

    def enqueue(self, movie, project_id=None):
        with self.connect() as db:
            db.execute('INSERT OR IGNORE INTO processing_queue(movie_key,movie_json,project_id,created_at,updated_at) VALUES(?,?,?,?,?)',
                       (self.key(movie), json.dumps(movie, ensure_ascii=False), project_id, now(), now()))
            row = dict(db.execute('SELECT * FROM processing_queue WHERE movie_key=?', (self.key(movie),)).fetchone())
        self.wake.set()
        return self.public(row)

    def public(self, row):
        movie = json.loads(row.pop('movie_json'))
        row['title'], row['year'] = movie['title'], movie.get('year')
        project = self.repository.get_by_id(row['project_id']) if row['project_id'] else None
        row['progress'] = project.get('progress_percent', 0) if project else 0
        row['step'] = project.get('notes', '') if project else 'Waiting for the previous movie'
        return row

    def list(self):
        with self.connect() as db:
            rows = db.execute('SELECT * FROM processing_queue ORDER BY id').fetchall()
        return [self.public(dict(row)) for row in rows]

    def retry(self, job_id):
        with self.connect() as db:
            updated = db.execute("UPDATE processing_queue SET state='QUEUED',error=NULL,updated_at=? WHERE id=? AND state='FAILED'", (now(), job_id)).rowcount
        if not updated:
            raise ValueError('Only failed jobs can be retried.')
        self.wake.set()

    def claim(self):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            if db.execute("SELECT 1 FROM processing_queue WHERE state='RUNNING'").fetchone():
                return None
            row = db.execute("SELECT * FROM processing_queue WHERE state='QUEUED' ORDER BY id LIMIT 1").fetchone()
            if not row:
                return None
            db.execute("UPDATE processing_queue SET state='RUNNING',updated_at=? WHERE id=?", (now(), row['id']))
            return dict(row)

    def process_next(self):
        job = self.claim()
        if not job:
            return False
        try:
            pid = job['project_id']
            if pid and not self.repository.get_by_id(pid):
                raise ValueError('This queued project was deleted. Select a different movie or restore the project.')
            if not pid:
                movie = json.loads(job['movie_json'])
                project = self.repository.create({'job_code': 'QUEUE-' + uuid.uuid4().hex[:8].upper(),
                    'title': 'Cinematic Review: ' + movie['title'], 'movie_count': 1,
                    'movies_json': [{**movie, 'slot': 1}], 'trailers_json': movie.get('trailers') or [],
                    'status': 'QUEUED', 'progress_percent': 0})
                pid = project['id']
                with self.connect() as db:
                    db.execute('UPDATE processing_queue SET project_id=? WHERE id=?', (pid, job['id']))
            # Queue completion means a local video is ready. Upload review remains separate.
            current = self.repository.get_by_id(pid)
            ready = current and current.get('status') == 'COMPLETED' and Path(current.get('final_video_path') or '').is_file()
            result = {'success': True} if ready else self.processor(project_id=pid, pipeline_mode='cinematic', auto_upload=False)
            project = self.repository.get_by_id(pid)
            if not result.get('success') or not project or not Path(project.get('final_video_path') or '').is_file():
                raise ValueError('Processing ended without a finished video file.')
            if self.publisher:
                self.publisher(pid)
            elif self.repository is project_repo:
                from app.services.publishing_automation_service import publishing_automation
                publishing_automation.enable(pid)
            with self.connect() as db:
                db.execute("UPDATE processing_queue SET state='COMPLETED',error=NULL,updated_at=? WHERE id=?", (now(), job['id']))
        except Exception as exc:
            logger.warning('Queue item %s failed: %s', job['id'], exc)
            with self.connect() as db:
                db.execute("UPDATE processing_queue SET state='FAILED',error=?,updated_at=? WHERE id=?", (str(exc)[:1200], now(), job['id']))
        return True

    def start_worker(self):
        with self.guard:
            if self.thread and self.thread.is_alive():
                return
            self.thread = threading.Thread(target=self._worker, name='single-movie-queue', daemon=True)
            self.thread.start()

    def _worker(self):
        # OS lock ensures even multiple backend processes cannot consume in parallel.
        lock_path = self.db_path.with_suffix('.queue.lock')
        with lock_path.open('a+b') as lock:
            lock.seek(0, 2)
            if lock.tell() == 0:
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
                    self.wake.wait(2); self.wake.clear()
            # Do not silently duplicate work interrupted during a backend restart.
            with self.connect() as db:
                db.execute("UPDATE processing_queue SET state='FAILED',error='Backend restarted during processing. Retry to resume this movie.',updated_at=? WHERE state='RUNNING'", (now(),))
            while True:
                try:
                    if self.process_next():
                        continue
                except Exception:
                    logger.exception('Queue worker will retry after database error')
                self.wake.wait(2); self.wake.clear()


processing_queue = ProcessingQueue()
