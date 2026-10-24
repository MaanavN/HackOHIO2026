"""Turn a reel into a structured opportunity (SPEC §3).

Stage A uses metadata + transcript only (cheap). Stage B adds sampled frames
for the vision model, and only runs when stage A isn't confident.
"""

import json
from pathlib import Path

from .. import host
from ..storage import data_dir
from . import download as dl
from . import media

CONFIDENT = 0.75

OPPORTUNITY_SCHEMA = {
    "type": "object",
    "properties": {
        "is_opportunity": {
            "type": "boolean",
            "description": "False if the reel isn't about a job, internship, fellowship, program or similar",
        },
        "company": {"type": "string"},
        "program": {"type": "string", "description": "Program or role name as advertised"},
        "role_type": {
            "type": "string",
            "description": "internship, full_time, part_time, fellowship, program, scholarship or other",
        },
        "location": {"type": "string"},
        "eligibility": {"type": "string", "description": "Who can apply (year, major, country...)"},
        "deadline": {"type": "string", "description": "ISO date if stated or clearly implied"},
        "urls_seen": {"type": "array", "items": {"type": "string"}},
        "on_screen_text": {"type": "array", "items": {"type": "string"}},
        "search_queries": {
            "type": "array",
            "items": {"type": "string"},
            "description": "2-4 web searches likely to find the official application page",
        },
        "confidence": {"type": "number", "description": "0-1 confidence in company + program"},
        "evidence": {"type": "string", "description": "Which sources (caption, transcript, frame N, comment) support this"},
    },
    "required": ["is_opportunity", "company", "program", "confidence", "evidence", "search_queries", "urls_seen"],
}

_INSTRUCTIONS = """You analyse an Instagram reel that may advertise a job, internship or other opportunity.
These reels often say "comment LINK and I'll DM you" and hide the actual link, so your job is to work out
WHICH opportunity it is so it can be searched for. Use every source given: caption, transcript, comments
(other users often post the real link or name the program), and frames if present (read on-screen text,
logos, screenshots of application pages, URLs in the background). Do not invent details; use an empty string
when something is unknown. Put every URL or domain you see in urls_seen. Write search_queries that would find the official
application page (company careers site or ATS), not news articles."""


def _transcribe(audio: Path | None) -> tuple[str, str | None]:
    """Returns (transcript, note). Uses Hermes's configured speech-to-text provider."""
    if audio is None:
        return "", "video has no audio track"
    try:
        from tools.transcription_tools import transcribe_audio
    except ImportError:
        return "", "transcription needs Hermes (not available when run standalone)"
    result = transcribe_audio(str(audio), source="apply")
    if not result.get("success"):
        return "", f"transcription failed: {result.get('error')}"
    return result.get("transcript", ""), None


def _text_block(meta: dict, transcript: str) -> str:
    comments = "\n".join(f"- @{c['author']}: {c['text']}" for c in meta["comments"]) or "(none fetched)"
    return (
        f"Reel: {meta['url']}\n"
        f"Posted by: {meta.get('uploader')} (@{meta.get('uploader_id')}) on {meta.get('upload_date')}\n"
        f"Uploader bio: {meta.get('uploader_biography') or '(none)'}\n"
        f"Uploader link: {meta.get('uploader_bio_url') or '(none)'}\n"
        f"Caption:\n{meta.get('caption') or '(empty)'}\n\n"
        f"Transcript:\n{transcript or '(none)'}\n\n"
        f"Top comments:\n{comments}"
    )


def _ask(text: str, frames: list[Path]) -> dict:
    client = host.llm()
    blocks = [{"type": "text", "text": text}]
    for i, frame in enumerate(frames, 1):
        blocks.append({"type": "text", "text": f"Frame {i}:"})
        blocks.append({"type": "image", "data": frame.read_bytes(), "mime_type": "image/jpeg"})
    result = client.complete_structured(
        instructions=_INSTRUCTIONS,
        input=blocks,
        json_schema=OPPORTUNITY_SCHEMA,
        schema_name="reel_opportunity",
        temperature=0.0,
        max_tokens=1500,
        purpose="apply.reel_analyze",
    )
    if result.parsed is None:
        raise RuntimeError(f"model did not return valid JSON: {result.text[:300]}")
    return result.parsed


def _confident(result: dict) -> bool:
    return bool(result.get("company")) and (result.get("confidence") or 0) >= CONFIDENT


def analyze(url: str, force_visual: bool = False, refresh: bool = False) -> dict:
    reels_dir = data_dir() / "reels"
    rid = dl.reel_id(url)
    cache = reels_dir / rid / "analysis.json" if rid else None
    if cache and cache.exists() and not refresh and not force_visual:
        return {**json.loads(cache.read_text()), "cached": True}

    meta = dl.download(
        url,
        reels_dir,
        cookies_file=host.setting("cookies_file"),
        cookies_browser=host.setting("cookies_from_browser"),
    )
    reel_dir = Path(meta["dir"])
    video = Path(meta["video_path"])
    notes = list(meta.get("notes") or [])

    audio = media.extract_audio(video, reel_dir)
    transcript, note = _transcribe(audio)
    if note:
        notes.append(note)

    out = {"metadata": meta, "transcript": transcript, "frames": [], "result": None, "stages": ["metadata"]}
    text = _text_block(meta, transcript)

    if host.llm() is None:
        out["frames"] = [str(p) for p in media.extract_frames(video, reel_dir)]
        out["stages"].append("frames")
        notes.append("no LLM available outside Hermes; returning raw metadata and frames only")
        out["notes"] = notes
        return out

    result = _ask(text, [])
    if force_visual or not _confident(result):
        frames = media.extract_frames(video, reel_dir)
        out["frames"] = [str(p) for p in frames]
        out["stages"].append("frames")
        result = _ask(text, frames)

    out["result"] = result
    out["notes"] = notes
    if cache:
        cache.write_text(json.dumps(out, indent=2, ensure_ascii=False))
    return out
