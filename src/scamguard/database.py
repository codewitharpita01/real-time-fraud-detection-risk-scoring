import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from .config import DB_PATH


def connect():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def connection():
    conn = connect()
    try:
        with conn:
            yield conn
    finally:
        conn.close()


def initialize():
    with connection() as conn:
        existing = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='analyses'").fetchone()
        if existing:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(analyses)")}
            if "signals_json" not in columns:
                # Preserve only high-level metadata when upgrading the earlier prototype.
                conn.execute("ALTER TABLE analyses RENAME TO analyses_legacy")
                conn.execute("""CREATE TABLE analyses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
                    category TEXT NOT NULL, assessment TEXT NOT NULL, score INTEGER NOT NULL,
                    signals_json TEXT NOT NULL, content_type TEXT NOT NULL,
                    verification_status TEXT NOT NULL
                )""")
                conn.execute("""INSERT INTO analyses(id,created_at,category,assessment,score,signals_json,content_type,verification_status)
                    SELECT id,created_at,category,assessment,score,'[]','text','Not verified' FROM analyses_legacy""")
                conn.execute("DROP TABLE analyses_legacy")
        conn.execute("""CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT, created_at TEXT NOT NULL,
            category TEXT NOT NULL, assessment TEXT NOT NULL, score INTEGER NOT NULL,
            signals_json TEXT NOT NULL, content_type TEXT NOT NULL,
            verification_status TEXT NOT NULL
        )""")
        conn.execute("""CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT, analysis_id INTEGER NOT NULL,
            helpful INTEGER NOT NULL CHECK(helpful IN (0,1)), created_at TEXT NOT NULL,
            FOREIGN KEY(analysis_id) REFERENCES analyses(id) ON DELETE CASCADE
        )""")


def save(result, content_type="text"):
    with connection() as conn:
        cur = conn.execute("""INSERT INTO analyses(created_at,category,assessment,score,signals_json,content_type,verification_status)
            VALUES(?,?,?,?,?,?,?)""", (
            datetime.now(timezone.utc).isoformat(), result["category"], result["risk_assessment"],
            result["indicative_score"], json.dumps(result["signals"], ensure_ascii=False),
            content_type, result.get("verification_status", "Not verified"),
        ))
        return cur.lastrowid


def add_feedback(analysis_id, helpful):
    with connection() as conn:
        conn.execute("INSERT INTO feedback(analysis_id,helpful,created_at) VALUES(?,?,?)", (
            int(analysis_id), int(bool(helpful)), datetime.now(timezone.utc).isoformat(),
        ))


def list_rows(search="", assessment="All", limit=500):
    query = "SELECT id,created_at,category,assessment,score,signals_json,content_type,verification_status FROM analyses WHERE 1=1"
    args = []
    if search:
        query += " AND (category LIKE ? OR signals_json LIKE ?)"
        args.extend([f"%{search}%"] * 2)
    if assessment != "All":
        query += " AND assessment = ?"
        args.append(assessment)
    query += " ORDER BY id DESC LIMIT ?"
    args.append(limit)
    with connection() as conn:
        return [dict(row) for row in conn.execute(query, args).fetchall()]


def summary():
    with connection() as conn:
        total = conn.execute("SELECT COUNT(*) FROM analyses").fetchone()[0]
        by_assessment = {row[0]: row[1] for row in conn.execute("SELECT assessment, COUNT(*) FROM analyses GROUP BY assessment")}
        by_category = {row[0]: row[1] for row in conn.execute("SELECT category, COUNT(*) FROM analyses GROUP BY category")}
        by_signal = {}
        for (raw,) in conn.execute("SELECT signals_json FROM analyses"):
            for signal in json.loads(raw):
                by_signal[signal] = by_signal.get(signal, 0) + 1
        feedback = conn.execute("SELECT COUNT(*), COALESCE(SUM(helpful),0) FROM feedback").fetchone()
    return {"total": total, "by_assessment": by_assessment, "by_category": by_category,
            "by_signal": by_signal, "feedback_count": feedback[0], "feedback_helpful": feedback[1]}


def delete_all():
    with connection() as conn:
        conn.execute("DELETE FROM feedback")
        conn.execute("DELETE FROM analyses")
