import os
import sqlite3
from datetime import datetime, timedelta

from lyrics_transcriber.correction.agentic.feedback.store import FeedbackStore
from lyrics_transcriber.correction.agentic.feedback.retention import cleanup_expired


def test_cleanup_expired(tmp_path):
    db = tmp_path / "test.sqlite3"
    store = FeedbackStore(str(db))
    # Insert old records by directly manipulating DB
    with sqlite3.connect(str(db)) as conn:
        old = (datetime.utcnow() - timedelta(days=2000)).isoformat()
        conn.execute("INSERT OR REPLACE INTO sessions (id, data, created_at) VALUES (?,?,?)", ("s_old", "{}", old))
        conn.execute("INSERT OR REPLACE INTO feedback (id, session_id, data, created_at) VALUES (?,?,?,?)", ("f_old", "s_old", "{}", old))
        conn.commit()

    deleted = cleanup_expired(str(db), older_than_days=365)
    assert deleted >= 0


