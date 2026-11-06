"""Call log in SQLite (stdlib): ended calls survive restarts and feed /api/sessions and /api/usage.

shortcut: one local file; use Postgres when running several server nodes (plans phase 04).
"""
import json
import sqlite3
import time
from pathlib import Path
from typing import Optional

from voxwire.core.config import settings

_COLUMNS = ["session_id", "api_key", "channel", "provider", "status", "end_reason", "created_at",
            "started_at", "ended_at", "duration_seconds", "metadata", "transcript"]
_conn: Optional[sqlite3.Connection] = None


def _db() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        Path(settings.DATA_DIR).mkdir(parents=True, exist_ok=True)
        _conn = sqlite3.connect(Path(settings.DATA_DIR) / "voxwire.db", check_same_thread=False)
        _conn.row_factory = sqlite3.Row
        _conn.execute(f"CREATE TABLE IF NOT EXISTS calls ({', '.join(_COLUMNS)}, PRIMARY KEY (session_id))")
        _conn.execute("CREATE INDEX IF NOT EXISTS calls_key_time ON calls (api_key, created_at)")
    return _conn


def reset(path_dir: str) -> None:
    """Point the store at another directory (tests)."""
    global _conn
    settings.DATA_DIR, _conn = path_dir, None


def save(s) -> None:
    row = (s.id, s.api_key, s.channel, s.provider, s.status, s.end_reason, s.created_at, s.started_at,
           s.ended_at, s.duration, json.dumps(s.metadata), json.dumps(s.transcript))
    with _db() as db:
        db.execute(f"INSERT OR REPLACE INTO calls VALUES ({', '.join('?' * len(_COLUMNS))})", row)


def _row(r: sqlite3.Row) -> dict:
    d = dict(r)
    d["metadata"], d["transcript"] = json.loads(d["metadata"]), json.loads(d["transcript"])
    d.pop("api_key")
    return d


def get(session_id: str, api_key: str) -> Optional[dict]:
    r = _db().execute("SELECT * FROM calls WHERE session_id = ?", (session_id,)).fetchone()
    if r and (api_key == "dev" or r["api_key"] == api_key):
        return _row(r)
    return None


def recent(api_key: str, limit: int = 50) -> list[dict]:
    where, args = ("", ()) if api_key == "dev" else ("WHERE api_key = ?", (api_key,))
    rows = _db().execute(f"SELECT * FROM calls {where} ORDER BY created_at DESC LIMIT ?", (*args, limit))
    return [_row(r) for r in rows]


def usage(api_key: str, days: int = 30) -> dict:
    since = time.time() - days * 86400
    where, args = ("created_at >= ?", (since,)) if api_key == "dev" else (
        "created_at >= ? AND api_key = ?", (since, api_key))
    per_day = _db().execute(
        f"SELECT date(created_at, 'unixepoch') AS day, COUNT(*) AS calls, "
        f"ROUND(SUM(duration_seconds) / 60.0, 2) AS minutes FROM calls WHERE {where} GROUP BY day ORDER BY day",
        args,
    ).fetchall()
    days_list = [dict(r) for r in per_day]
    return {
        "days": days,
        "calls": sum(d["calls"] for d in days_list),
        "minutes": round(sum(d["minutes"] or 0 for d in days_list), 2),
        "per_day": days_list,
    }
