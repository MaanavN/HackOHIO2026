"""The user's candidate profile (SPEC §1), stored as profile.json in the data dir."""

import json

from .storage import data_dir

# Fields most application forms ask for. Dotted paths into the profile dict.
REQUIRED_FIELDS = (
    "contact.name",
    "contact.email",
    "contact.phone",
    "contact.location",
    "education",
    "experience",
    "skills",
    "work_authorization",
    "graduation_date",
    "target_roles",
)

# Asked once before any auto-fill, but never required to use the bot.
OPTIONAL_FIELDS = (
    "contact.address",
    "contact.linkedin",
    "contact.github",
    "contact.website",
    "salary_expectation",
    "availability",
    "requires_sponsorship",
    "eeo",
)

PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "contact": {
            "type": "object",
            "properties": {
                k: {"type": "string"}
                for k in ("name", "email", "phone", "location", "address", "linkedin", "github", "website")
            },
        },
        "education": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    k: {"type": "string"} for k in ("school", "degree", "major", "gpa", "start", "end")
                },
            },
        },
        "experience": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "company": {"type": "string"},
                    "title": {"type": "string"},
                    "start": {"type": "string"},
                    "end": {"type": "string"},
                    "bullets": {"type": "array", "items": {"type": "string"}},
                },
            },
        },
        "projects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "tech": {"type": "array", "items": {"type": "string"}},
                    "link": {"type": "string"},
                },
            },
        },
        "skills": {"type": "array", "items": {"type": "string"}},
        "graduation_date": {"type": "string"},
        "work_authorization": {"type": "string"},
        "requires_sponsorship": {"type": "boolean"},
        "target_roles": {"type": "array", "items": {"type": "string"}},
        "salary_expectation": {"type": "string"},
        "availability": {"type": "string"},
        "notes": {"type": "array", "items": {"type": "string"}},
    },
}


def _path():
    return data_dir() / "profile.json"


def load() -> dict:
    path = _path()
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def save(profile: dict) -> None:
    _path().write_text(json.dumps(profile, indent=2, ensure_ascii=False))


def _merge(base, new):
    """Dicts merge recursively, lists append new unique items, scalars are replaced."""
    if isinstance(base, dict) and isinstance(new, dict):
        out = dict(base)
        for key, value in new.items():
            out[key] = _merge(base.get(key), value) if key in base else value
        return out
    if isinstance(base, list) and isinstance(new, list):
        out = list(base)
        for item in new:
            if item not in out:
                out.append(item)
        return out
    return base if new in (None, "", [], {}) else new


def merge(updates: dict, replace: bool = False) -> dict:
    """Merge updates into the stored profile. replace=True overwrites top-level keys instead."""
    current = load()
    merged = {**current, **updates} if replace else _merge(current, updates)
    save(merged)
    return merged


def _lookup(profile: dict, dotted: str):
    value = profile
    for part in dotted.split("."):
        if not isinstance(value, dict):
            return None
        value = value.get(part)
    return value


def missing_fields(profile: dict | None = None) -> dict:
    profile = load() if profile is None else profile
    empty = (None, "", [], {})
    return {
        "required": [f for f in REQUIRED_FIELDS if _lookup(profile, f) in empty],
        "optional": [f for f in OPTIONAL_FIELDS if _lookup(profile, f) in empty],
    }


def summary(profile: dict | None = None) -> str:
    """A few lines about the user, cheap enough to inject into a prompt."""
    profile = load() if profile is None else profile
    if not profile:
        return ""
    lines = []
    name = _lookup(profile, "contact.name")
    if name:
        lines.append(f"Name: {name}")
    for edu in (profile.get("education") or [])[:2]:
        parts = [edu.get("degree"), edu.get("major"), edu.get("school")]
        when = f" (ends {edu['end']})" if edu.get("end") else ""
        lines.append("Education: " + ", ".join(p for p in parts if p) + when)
    for exp in (profile.get("experience") or [])[:3]:
        lines.append(f"Experience: {exp.get('title', '')} at {exp.get('company', '')}".strip())
    if profile.get("skills"):
        lines.append("Skills: " + ", ".join(profile["skills"][:15]))
    if profile.get("target_roles"):
        lines.append("Targets: " + ", ".join(profile["target_roles"]))
    if profile.get("work_authorization"):
        lines.append(f"Work authorization: {profile['work_authorization']}")
    return "\n".join(lines)
