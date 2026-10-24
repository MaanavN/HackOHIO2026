"""Application tracker (SPEC §6): one SQLite table of opportunities and their status."""

from datetime import datetime, timezone

from .reel.download import reel_id
from .storage import connect

STATUSES = (
    "found",
    "awaiting_confirmation",
    "applied",
    "assisted",
    "skipped",
    "interview",
    "rejected",
    "offer",
)

EDITABLE = ("company", "role", "apply_url", "reel_url", "deadline", "status", "job_description", "notes")

_SCHEMA = """
CREATE TABLE IF NOT EXISTS applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    reel_url TEXT,
    company TEXT NOT NULL,
    role TEXT,
    apply_url TEXT,
    deadline TEXT,
    status TEXT NOT NULL DEFAULT 'found',
    job_description TEXT,
    notes TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
)
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _db():
    conn = connect()
    conn.execute(_SCHEMA)
    return conn


def _check_status(status: str | None) -> None:
    if status is not None and status not in STATUSES:
        raise ValueError(f"status must be one of {', '.join(STATUSES)}")


def save(company: str, **fields) -> dict:
    """Insert an application, or update the existing one with the same apply_url / reel_url."""
    if not company:
        raise ValueError("company is required")
    _check_status(fields.get("status"))
    fields = {k: v for k, v in fields.items() if k in EDITABLE and v not in (None, "")}

    with _db() as conn:
        existing = None
        for key in ("apply_url", "reel_url"):
            if fields.get(key):
                existing = conn.execute(
                    f"SELECT id FROM applications WHERE {key} = ? AND company = ?", (fields[key], company)
                ).fetchone()
                if existing:
                    break
        if not existing:
            now = _now()
            cols = ["company", *fields, "created_at", "updated_at"]
            vals = [company, *fields.values(), now, now]
            cur = conn.execute(
                f"INSERT INTO applications ({', '.join(cols)}) VALUES ({', '.join('?' * len(cols))})", vals
            )
            conn.commit()
            return get(cur.lastrowid)
    return update(existing["id"], **fields)


def update(app_id: int, **fields) -> dict:
    _check_status(fields.get("status"))
    fields = {k: v for k, v in fields.items() if k in EDITABLE and v is not None}
    if not get(app_id):
        raise ValueError(f"no application with id {app_id}")
    if fields:
        fields["updated_at"] = _now()
        sets = ", ".join(f"{k} = ?" for k in fields)
        with _db() as conn:
            conn.execute(f"UPDATE applications SET {sets} WHERE id = ?", [*fields.values(), app_id])
    return get(app_id)


def get(app_id: int) -> dict | None:
    with _db() as conn:
        row = conn.execute("SELECT * FROM applications WHERE id = ?", (app_id,)).fetchone()
    return dict(row) if row else None


def find(query: str) -> list[dict]:
    """Look up by numeric id or by a case-insensitive company/role substring."""
    query = query.strip()
    if query.isdigit():
        row = get(int(query))
        return [row] if row else []
    like = f"%{query}%"
    with _db() as conn:
        rows = conn.execute(
            "SELECT * FROM applications WHERE company LIKE ? OR role LIKE ? ORDER BY updated_at DESC",
            (like, like),
        ).fetchall()
    return [dict(r) for r in rows]


def find_by_reel(rid: str) -> list[dict]:
    with _db() as conn:
        rows = conn.execute("SELECT * FROM applications WHERE reel_url IS NOT NULL").fetchall()
    return [dict(r) for r in rows if reel_id(r["reel_url"]) == rid]


def list_all(status: str | None = None) -> list[dict]:
    _check_status(status)
    with _db() as conn:
        if status:
            rows = conn.execute(
                "SELECT * FROM applications WHERE status = ? ORDER BY updated_at DESC", (status,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM applications ORDER BY updated_at DESC").fetchall()
    return [dict(r) for r in rows]


def summary_line(app: dict) -> str:
    role = f" — {app['role']}" if app.get("role") else ""
    deadline = f" (due {app['deadline']})" if app.get("deadline") else ""
    return f"#{app['id']} {app['company']}{role} [{app['status']}]{deadline}"
