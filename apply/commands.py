"""Slash commands (SPEC §6). They work in Telegram, the CLI and every other Hermes surface."""

import json

from . import profile, tracker

MEMORY_IMPORT_PROMPT = """List everything you know about me that would matter to a recruiter or a job application. Include:
- my name, location, and contact links you know about
- education (school, degree, major, graduation date, GPA, relevant courses)
- work experience and internships, with what I actually did
- projects, with the technologies I used
- technical and soft skills
- the kinds of roles, companies and industries I'm interested in
- my work authorization / visa situation, if you know it
- anything else I've told you about my career goals, strengths or preferences
Reply as a plain list of facts. Don't guess; leave out anything you don't actually know."""


def jobs(raw_args: str) -> str:
    status = raw_args.strip() or None
    try:
        apps = tracker.list_all(status)
    except ValueError as e:
        return str(e)
    if not apps:
        return "No applications yet. Send me an Instagram reel link to get started."
    return "\n".join(tracker.summary_line(a) for a in apps)


def status(raw_args: str) -> str:
    query = raw_args.strip()
    if not query:
        return "Usage: /job <company or id>"
    apps = tracker.find(query)
    if not apps:
        return f"No application matches {query!r}."
    lines = []
    for app in apps[:5]:
        lines.append(tracker.summary_line(app))
        for key in ("apply_url", "reel_url", "notes"):
            if app.get(key):
                lines.append(f"  {key}: {app[key]}")
        lines.append(f"  updated: {app['updated_at']}")
    return "\n".join(lines)


def update(raw_args: str) -> str:
    parts = raw_args.strip().rsplit(maxsplit=1)
    if len(parts) != 2:
        return f"Usage: /setstatus <company or id> <status>\nStatuses: {', '.join(tracker.STATUSES)}"
    query, new_status = parts
    if new_status not in tracker.STATUSES:
        return f"Unknown status {new_status!r}. Use one of: {', '.join(tracker.STATUSES)}"
    apps = tracker.find(query)
    if not apps:
        return f"No application matches {query!r}."
    if len(apps) > 1:
        return "Several match; use the id:\n" + "\n".join(tracker.summary_line(a) for a in apps)
    app = tracker.update(apps[0]["id"], status=new_status)
    return "Updated: " + tracker.summary_line(app)


def show_profile(raw_args: str) -> str:
    data = profile.load()
    if not data:
        return "No profile yet. Send me your resume (PDF or DOCX), or run /import_memory."
    missing = profile.missing_fields(data)
    text = profile.summary(data) or json.dumps(data, indent=2)[:1500]
    if missing["required"]:
        text += "\n\nStill missing: " + ", ".join(missing["required"])
    return text


def import_memory(raw_args: str) -> str:
    return (
        "Paste this into ChatGPT, Gemini or Claude, then send me its whole answer:\n\n" + MEMORY_IMPORT_PROMPT
    )


# /status, /update and /profile are built-in Hermes commands, so these use other names.
COMMANDS = (
    ("jobs", jobs, "List tracked applications", "[status]"),
    ("job", status, "Details for one application", "<company or id>"),
    ("setstatus", update, "Change an application's status", "<company or id> <status>"),
    ("me", show_profile, "Show your stored candidate profile", ""),
    ("import_memory", import_memory, "Get a prompt to import what other AIs know about you", ""),
)
