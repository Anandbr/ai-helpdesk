import json
import os
from db import get_db, init_db
from models import Policy, Closure

SEED_PATH = os.path.join(
    os.path.dirname(__file__),
    "data", "seed_kb.json"
)

def seed():
    init_db()

    with open(SEED_PATH) as f:
        data = json.load(f)

    # Validate ALL rows through Pydantic first
    # Bad seed kills boot loudly not silently
    policies = [Policy(**p) for p in data["policies"]]
    closures = [Closure(**c) for c in data["closures"]]

    with get_db() as conn:
        for p in policies:
            conn.execute(
                """INSERT OR IGNORE INTO policies
                   (id, topic, title, content, action,
                    sensitivity, escalation_contact,
                    last_verified, expires)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    p.id, p.topic, p.title, p.content,
                    p.action, p.sensitivity,
                    p.escalation_contact,
                    p.last_verified.isoformat(),
                    p.expires.isoformat()
                    if p.expires else None,
                )
            )

        for c in closures:
            existing = conn.execute(
                "SELECT id FROM closures WHERE name = ?",
                (c.name,)
            ).fetchone()
            if not existing:
                conn.execute(
                    'INSERT INTO closures '
                    '(name, date, start, "end") '
                    'VALUES (?, ?, ?, ?)',
                    (
                        c.name,
                        c.date.isoformat() if c.date else None,
                        c.start.isoformat() if c.start else None,
                        c.end.isoformat() if c.end else None,
                    )
                )
    print(
        f"Seed complete: {len(policies)} policies, "
        f"{len(closures)} closures."
    )

if __name__ == "main":
    seed()
