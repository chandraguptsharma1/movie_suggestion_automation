# Single-movie automatic queue

Open **Movie Search**, choose a year/category if needed, and click a movie. Selection immediately adds one movie to the persistent queue. Each movie becomes its own Cinematic Review project. **Add Movie to Queue** in the header opens this search page.

**Processing Queue** in the sidebar shows waiting, running, failed and video-ready jobs. The backend processes FIFO, with at most one queue job running. An OS lock prevents two backend worker processes from consuming the queue simultaneously; a transactional SQLite claim also protects each job. Clicking the same movie again reuses its queue entry. Failed jobs do not block later movies and have a Retry button that reuses their existing project and downloaded sources.

Queue state survives page reloads and browser closure. The backend must remain running. If the backend restarts mid-job, that interrupted item is marked failed with an explanation and can be retried; waiting movies continue automatically. This avoids silently repeating interrupted operations. Completed existing projects are reused without rendering them again.

Queue processing creates a local video only. Thumbnail/copyright verification and YouTube publication are separate steps. Existing group lineups remain available to view, but the primary creation flow is now single-movie selection.

Storage: `processing_queue` table in the project's existing SQLite database. API: `GET/POST /api/processing-queue`, `POST /api/processing-queue/project/{id}`, and `POST /api/processing-queue/{id}/retry`.
