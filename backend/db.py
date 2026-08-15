import json
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta

DB_PATH = os.getenv(
    "DB_PATH",
    os.path.join(os.path.dirname(__file__), "data", "frontdek.db")
)

SCHEMA = """
PRAGMA journal_mode=WAL;

CREATE TABLE IF NOT EXISTS policies (
    id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    action TEXT NOT NULL,
    sensitivity TEXT NOT NULL,
    escalation_contact TEXT,
    last_verified TEXT NOT NULL,
    expires TEXT
);

CREATE TABLE IF NOT EXISTS closures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    date TEXT,
    start TEXT,
    "end" TEXT
);

CREATE TABLE IF NOT EXISTS question_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    source_policy_ids TEXT NOT NULL,
    action_taken TEXT NOT NULL,
    confidence TEXT NOT NULL,
    escalation_reason TEXT,
    timestamp TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS gap_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_log_id INTEGER NOT NULL,
    question TEXT NOT NULL,
    normalized_question TEXT NOT NULL,
    count INTEGER NOT NULL DEFAULT 1,
    status TEXT NOT NULL DEFAULT 'pending',
    operator_note TEXT,
    created_at TEXT NOT NULL,
    resolved_at TEXT,
    FOREIGN KEY (question_log_id) REFERENCES question_log(id)
);
"""

@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def init_db():
    os.makedirs(
        os.path.dirname(DB_PATH),
        exist_ok=True
    )
    with get_db() as conn:
        conn.executescript(SCHEMA)

def _normalize(text: str) -> str:
    """
    Normalize question text for gap dedup.
    lowercase, strip punctuation,
    collapse whitespace.
    """
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ─────────────────────────────────────────
# Policy queries
# ─────────────────────────────────────────
def get_all_policies() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM policies ORDER BY topic, id"
        ).fetchall()
    return [dict(r) for r in rows]

def get_policy(policy_id: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM policies WHERE id = ?",
            (policy_id,)
        ).fetchone()
    return dict(row) if row else None

ALLOWED_POLICY_COLUMNS = {
    "title", "content", "action",
    "escalation_contact", "expires",
    "last_verified"
}

def update_policy(policy_id: str, updates: dict):
    disallowed = set(updates) - ALLOWED_POLICY_COLUMNS
    if disallowed:
        raise ValueError(
            f"disallowed columns: {disallowed}"
        )
    updates = {
        **updates,
        "last_verified": datetime.now().date().isoformat()
    }
    set_clauses = ", ".join(
        f"{k} = ?" for k in updates.keys()
    )
    values = list(updates.values()) + [policy_id]
    with get_db() as conn:
        conn.execute(
            f"UPDATE policies SET {set_clauses} WHERE id = ?",
            values
        )

def create_policy(policy) -> None:
    with get_db() as conn:
        conn.execute(
            """INSERT INTO policies
               (id, topic, title, content, action,
                sensitivity, escalation_contact,
                last_verified, expires)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                policy.id, policy.topic, policy.title,
                policy.content, policy.action,
                policy.sensitivity, policy.escalation_contact,
                policy.last_verified.isoformat(),
                policy.expires.isoformat()
                if policy.expires else None,
            )
        )

# ─────────────────────────────────────────
# Closure queries
# ─────────────────────────────────────────
def get_all_closures() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            'SELECT * FROM closures ORDER BY date, start'
        ).fetchall()
    return [dict(r) for r in rows]


def is_closed_on(date_str: str) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM closures WHERE date = ?",
            (date_str,)
        ).fetchone()
        if row:
            return dict(row)
        row = conn.execute(
            'SELECT * FROM closures '
            'WHERE start <= ? AND "end" >= ?',
            (date_str, date_str)
        ).fetchone()
    return dict(row) if row else None

# ─────────────────────────────────────────
# Question log queries
# ─────────────────────────────────────────
def insert_question_log(
    question: str,
    answer: str,
    source_policy_ids: list[str],
    action_taken: str,
    confidence: str,
    escalation_reason: str | None = None,
) -> int:
    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO question_log
               (question, answer, source_policy_ids,
                action_taken, confidence,
                escalation_reason, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                question,
                answer,
                json.dumps(source_policy_ids),
                action_taken,
                confidence,
                escalation_reason,
                datetime.now().isoformat(),
            )
        )
        new_id = cursor.lastrowid
    return new_id


def get_all_questions(limit: int = 100) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM question_log
               ORDER BY timestamp DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["source_policy_ids"] = json.loads(
            d["source_policy_ids"]
        )
        result.append(d)
    return result


def get_flagged_questions(limit: int = 100) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM question_log
               WHERE action_taken IN
               ('answer_then_flag','escalate','emergency')
               ORDER BY timestamp DESC
               LIMIT ?""",
            (limit,)
        ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["source_policy_ids"] = json.loads(
            d["source_policy_ids"]
        )
        result.append(d)
    return result

# ─────────────────────────────────────────
# Gap entry queries
# ─────────────────────────────────────────
def insert_or_increment_gap(
    question_log_id: int,
    question: str,
) -> None:
    normalized = _normalize(question)

    with get_db() as conn:
        existing = conn.execute(
            """SELECT id FROM gap_entries
               WHERE normalized_question = ?
               AND status = 'pending'""",
            (normalized,)
        ).fetchone()

        if existing:
            conn.execute(
                """UPDATE gap_entries
                   SET count = count + 1,
                       question_log_id = ?
                   WHERE id = ?""",
                (question_log_id, existing["id"])
            )
        else:
            conn.execute(
                """INSERT INTO gap_entries
                   (question_log_id, question,
                    normalized_question,
                    count, status, created_at)
                   VALUES (?, ?, ?, 1, 'pending', ?)""",
                (
                    question_log_id,
                    question,
                    normalized,
                    datetime.now().isoformat(),
                )
            )


def get_all_gaps() -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM gap_entries
               ORDER BY count DESC, created_at DESC"""
        ).fetchall()
    return [dict(r) for r in rows]


def update_gap_status(
    gap_id: int,
    status: str,
    operator_note: str | None = None,
) -> None:
    resolved_at = (
        datetime.now().isoformat()
        if status != "pending"
        else None
    )
    with get_db() as conn:
        conn.execute(
            """UPDATE gap_entries
               SET status = ?,
                   operator_note = ?,
                   resolved_at = ?
               WHERE id = ?""",
            (status, operator_note, resolved_at, gap_id)
        )


def get_stale_policies() -> list[dict]:
    soon = (
        datetime.now().date() + timedelta(days=30)
    ).isoformat()
    with get_db() as conn:
        rows = conn.execute(
            """SELECT * FROM policies
               WHERE expires IS NOT NULL
               AND expires <= ?
               ORDER BY expires""",
            (soon,)
        ).fetchall()
    return [dict(r) for r in rows]