"""Tool handlers. Each takes the model's args and returns a JSON string, never raising."""

import json
import logging

from . import host, profile, resume, tracker
from .reel import analyze as reel
from .reel import download as reels
from .storage import data_dir

logger = logging.getLogger(__name__)


def _ok(**data) -> str:
    return json.dumps(data, ensure_ascii=False, default=str)


def _err(message: str) -> str:
    return json.dumps({"error": message}, ensure_ascii=False)


def _safe(fn):
    def wrapper(args: dict, **kwargs) -> str:
        try:
            return fn(dict(args or {}))
        except Exception as e:
            logger.exception("apply tool %s failed", fn.__name__)
            return _err(f"{type(e).__name__}: {e}")

    wrapper.__name__ = fn.__name__
    return wrapper


@_safe
def reel_analyze(args: dict) -> str:
    url = (args.get("url") or "").strip()
    if not url:
        return _err("url is required")
    out = reel.analyze(url, force_visual=bool(args.get("force_visual")), refresh=bool(args.get("refresh")))
    meta = out["metadata"]
    existing = [tracker.summary_line(a) for a in tracker.find_by_reel(meta["id"])]
    return _ok(
        result=out["result"],
        caption=meta["caption"],
        uploader=meta.get("uploader_id"),
        uploader_profile_url=meta.get("uploader_profile_url"),
        uploader_bio=meta.get("uploader_biography"),
        uploader_bio_url=meta.get("uploader_bio_url"),
        upload_date=meta.get("upload_date"),
        comments=meta["comments"][:10],
        transcript=out["transcript"][:3000],
        frames_analyzed=len(out["frames"]),
        stages=out["stages"],
        notes=out.get("notes", []),
        cached=out.get("cached", False),
        already_tracked=existing,
    )


@_safe
def reel_cleanup(args: dict) -> str:
    url = (args.get("url") or "").strip()
    if not url:
        return _err("url is required")
    return _ok(**reels.discard(url, data_dir() / "reels"))


@_safe
def application_save(args: dict) -> str:
    company = args.pop("company", "")
    app = tracker.save(company, **args)
    return _ok(application=app, summary=tracker.summary_line(app))


@_safe
def application_update(args: dict) -> str:
    app_id = args.pop("id", None)
    if app_id is None:
        return _err("id is required")
    app = tracker.update(int(app_id), **args)
    return _ok(application=app, summary=tracker.summary_line(app))


@_safe
def applications_list(args: dict) -> str:
    query = (args.get("query") or "").strip()
    apps = tracker.find(query) if query else tracker.list_all(args.get("status"))
    if query and args.get("status"):
        apps = [a for a in apps if a["status"] == args["status"]]
    for app in apps:
        if app.get("job_description") and len(app["job_description"]) > 500:
            app["job_description"] = app["job_description"][:500] + "…"
    return _ok(count=len(apps), applications=apps)


@_safe
def profile_get(args: dict) -> str:
    data = profile.load()
    return _ok(profile=data, missing=profile.missing_fields(data), empty=not data)


@_safe
def profile_update(args: dict) -> str:
    updates = args.get("updates")
    if not isinstance(updates, dict) or not updates:
        return _err("updates must be a non-empty object")
    data = profile.merge(updates, replace=bool(args.get("replace")))
    return _ok(profile=data, missing=profile.missing_fields(data))


@_safe
def resume_import(args: dict) -> str:
    text = resume.extract_text(args.get("file_path") or "")
    client = host.llm()
    if client is None:
        return _err("resume parsing needs Hermes's LLM access")
    result = client.complete_structured(
        instructions=(
            "Extract the candidate's profile from this resume. Copy facts exactly; do not invent "
            "anything. Keep experience bullets close to the original wording. Leave out fields "
            "the resume doesn't state."
        ),
        input=[{"type": "text", "text": text}],
        json_schema=profile.PROFILE_SCHEMA,
        schema_name="candidate_profile",
        temperature=0.0,
        max_tokens=4000,
        purpose="apply.resume_import",
    )
    if result.parsed is None:
        return _err(f"could not parse the resume: {result.text[:300]}")
    data = profile.merge(result.parsed)
    return _ok(extracted=result.parsed, missing=profile.missing_fields(data))
