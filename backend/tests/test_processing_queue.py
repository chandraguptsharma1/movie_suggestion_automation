import threading
from app.services.processing_queue_service import ProcessingQueue


class Repository:
    def __init__(self):
        self.projects = {}
    def create(self, data):
        pid = len(self.projects) + 1
        self.projects[pid] = {'id': pid, **data}
        return self.projects[pid]
    def get_by_id(self, pid):
        return self.projects.get(pid)


def test_fifo_duplicate_and_only_one_active_processor(tmp_path):
    repo = Repository()
    started, finish = threading.Event(), threading.Event()
    calls = []
    def process(project_id, pipeline_mode, auto_upload):
        assert pipeline_mode == 'cinematic' and auto_upload is False
        calls.append(project_id)
        if len(calls) == 1:
            started.set(); assert finish.wait(5)
        video = tmp_path / f'{project_id}.mp4'; video.write_bytes(b'finished')
        repo.projects[project_id].update(status='COMPLETED', final_video_path=str(video))
        return {'success': True}
    q = ProcessingQueue(tmp_path / 'queue.db', repo, process)
    first = q.enqueue({'tmdb_id': 1, 'title': 'First'})
    assert q.enqueue({'tmdb_id': 1, 'title': 'First'})['id'] == first['id']
    q.enqueue({'tmdb_id': 2, 'title': 'Second'})
    worker = threading.Thread(target=q.process_next)
    worker.start(); assert started.wait(5)
    assert q.process_next() is False
    assert [x['state'] for x in q.list()] == ['RUNNING', 'QUEUED']
    finish.set(); worker.join(5)
    assert q.process_next() is True
    assert calls == [1, 2]
    assert all(x['state'] == 'COMPLETED' for x in q.list())
    assert all(p['movie_count'] == 1 for p in repo.projects.values())


def test_failure_does_not_block_next_and_retry_reuses_project(tmp_path):
    repo = Repository()
    calls = []
    def process(project_id, **kwargs):
        calls.append(project_id)
        if len(calls) == 1:
            raise RuntimeError('Trailer unavailable')
        video = tmp_path / f'{project_id}.mp4'; video.write_bytes(b'finished')
        repo.projects[project_id].update(status='COMPLETED', final_video_path=str(video))
        return {'success': True}
    q = ProcessingQueue(tmp_path / 'queue.db', repo, process)
    a = q.enqueue({'tmdb_id': 1, 'title': 'First'})
    q.enqueue({'tmdb_id': 2, 'title': 'Second'})
    q.process_next(); q.process_next()
    assert [x['state'] for x in q.list()] == ['FAILED', 'COMPLETED']
    q.retry(a['id']); q.process_next()
    assert calls == [1, 2, 1] and len(repo.projects) == 2
    restored = ProcessingQueue(tmp_path / 'queue.db', repo, process)
    assert all(x['state'] == 'COMPLETED' for x in restored.list())


def test_existing_finished_project_is_not_rendered_or_uploaded_again(tmp_path):
    repo = Repository()
    video = tmp_path / 'ready.mp4'; video.write_bytes(b'finished')
    p = repo.create({'status': 'COMPLETED', 'final_video_path': str(video)})
    def should_not_run(**kwargs):
        raise AssertionError('Already finished')
    q = ProcessingQueue(tmp_path / 'queue.db', repo, should_not_run)
    q.enqueue({'tmdb_id': 1, 'title': 'Existing'}, p['id'])
    q.process_next()
    assert q.list()[0]['state'] == 'COMPLETED'
