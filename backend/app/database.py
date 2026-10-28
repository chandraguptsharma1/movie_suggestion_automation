import json
import sqlite3
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)

DB_PATH = settings.storage_path / "movie_suggestion.db"

def init_db():
    """Initialize SQLite database schema."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_code TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                notes TEXT DEFAULT '',
                movie_count INTEGER DEFAULT 0,
                movies_json TEXT DEFAULT '[]',
                trailers_json TEXT DEFAULT '[]',
                audience_reviews_json TEXT DEFAULT '{}',
                script_text TEXT DEFAULT '',
                script_data_json TEXT DEFAULT '{}',
                voice_audio_path TEXT DEFAULT '',
                voice_data_json TEXT DEFAULT '{}',
                thumbnail_path TEXT DEFAULT '',
                thumbnail_data_json TEXT DEFAULT '{}',
                source_videos_json TEXT DEFAULT '[]',
                scenes_json TEXT DEFAULT '[]',
                final_video_path TEXT DEFAULT '',
                status TEXT DEFAULT 'CREATED',
                progress_percent INTEGER DEFAULT 10,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        # Ensure scenes_json column exists in case database already exists
        cursor.execute("PRAGMA table_info(projects)")
        cols = [col[1] for col in cursor.fetchall()]
        if "scenes_json" not in cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN scenes_json TEXT DEFAULT '[]'")
        if "bgm_data_json" not in cols:
            cursor.execute("ALTER TABLE projects ADD COLUMN bgm_data_json TEXT DEFAULT '{}'")
        conn.commit()


@contextmanager
def get_connection():
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class ProjectRepository:
    def __init__(self):
        init_db()

    def _row_to_dict(self, row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        for json_col in [
            "movies_json",
            "trailers_json",
            "audience_reviews_json",
            "script_data_json",
            "voice_data_json",
            "thumbnail_data_json",
            "source_videos_json",
            "scenes_json",
            "bgm_data_json",
        ]:
            if d.get(json_col):
                try:
                    d[json_col] = json.loads(d[json_col])
                except Exception:
                    pass
        return d

    def create(self, data: Dict[str, Any]) -> Dict[str, Any]:
        now = datetime.now(timezone.utc).isoformat()
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO projects (
                    job_code, title, notes, movie_count, movies_json, trailers_json,
                    audience_reviews_json, script_text, script_data_json, voice_audio_path,
                    voice_data_json, thumbnail_path, thumbnail_data_json, source_videos_json,
                    scenes_json, final_video_path, status, progress_percent, created_at, updated_at
                ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    data.get("job_code", ""),
                    data.get("title", "Untitled Project"),
                    data.get("notes", ""),
                    data.get("movie_count", 0),
                    json.dumps(data.get("movies_json", [])),
                    json.dumps(data.get("trailers_json", [])),
                    json.dumps(data.get("audience_reviews_json", {})),
                    data.get("script_text", ""),
                    json.dumps(data.get("script_data_json", {})),
                    data.get("voice_audio_path", ""),
                    json.dumps(data.get("voice_data_json", {})),
                    data.get("thumbnail_path", ""),
                    json.dumps(data.get("thumbnail_data_json", {})),
                    json.dumps(data.get("source_videos_json", [])),
                    json.dumps(data.get("scenes_json", [])),
                    data.get("final_video_path", ""),
                    data.get("status", "CREATED"),
                    data.get("progress_percent", 10),
                    now,
                    now,
                ),
            )
            project_id = cursor.lastrowid
            conn.commit()
            return self.get_by_id(project_id)

    def get_by_id(self, project_id: int) -> Optional[Dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_dict(row)

    def list_all(self, limit: int = 100) -> List[Dict[str, Any]]:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM projects ORDER BY id DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [self._row_to_dict(r) for r in rows]

    def update(self, project_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        fields = []
        values = []
        now = datetime.now(timezone.utc).isoformat()
        updates["updated_at"] = now

        for k, v in updates.items():
            fields.append(f"{k} = ?")
            if isinstance(v, (dict, list)):
                values.append(json.dumps(v))
            else:
                values.append(v)

        values.append(project_id)

        with get_connection() as conn:
            cursor = conn.cursor()
            query = f"UPDATE projects SET {', '.join(fields)} WHERE id = ?"
            cursor.execute(query, values)
            conn.commit()
            return self.get_by_id(project_id)

    def delete(self, project_id: int) -> bool:
        with get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
            conn.commit()
            return cursor.rowcount > 0


project_repo = ProjectRepository()
