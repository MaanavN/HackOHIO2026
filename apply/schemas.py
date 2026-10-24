"""Tool schemas: what the model reads to decide when and how to call each tool."""

from .tracker import STATUSES

REEL_ANALYZE = {
    "name": "reel_analyze",
    "description": (
        "Download an Instagram reel and work out which job/internship/program it advertises. "
        "Reads the caption, uploader, comments and audio transcript first; if that isn't conclusive "
        "it also samples frames and reads on-screen text, logos and URLs with a vision model. "
        "Returns company, program, deadline, URLs seen and suggested web searches for the official "
        "application page. Call this whenever the user sends an instagram.com/reel/ or /p/ link."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "url": {"type": "string", "description": "The Instagram reel or post URL"},
            "force_visual": {
                "type": "boolean",
                "description": "Also analyse frames even if the metadata looks conclusive",
            },
            "refresh": {"type": "boolean", "description": "Ignore a cached analysis of this reel"},
        },
        "required": ["url"],
    },
}

REEL_CLEANUP = {
    "name": "reel_cleanup",
    "description": (
        "Delete the local working files for a reel — the downloaded video, extracted audio, "
        "sampled frames and cached analysis. Call once you are finished with the reel: after "
        "applying, assisting or skipping it, and when it turns out not to be an opportunity. "
        "The tracker entry and its reel_url stay."
    ),
    "parameters": {
        "type": "object",
        "properties": {"url": {"type": "string", "description": "The Instagram reel or post URL"}},
        "required": ["url"],
    },
}

_APP_FIELDS = {
    "company": {"type": "string"},
    "role": {"type": "string", "description": "Program or role name"},
    "apply_url": {"type": "string", "description": "Official application page"},
    "reel_url": {"type": "string", "description": "The reel this came from"},
    "deadline": {"type": "string", "description": "ISO date"},
    "status": {"type": "string", "enum": list(STATUSES)},
    "job_description": {"type": "string", "description": "Full text of the listing, kept for interview prep"},
    "notes": {"type": "string"},
}

APPLICATION_SAVE = {
    "name": "application_save",
    "description": (
        "Save an opportunity to the user's application tracker, or update it if the same apply_url "
        "or reel_url is already saved. Call after you find the official application page."
    ),
    "parameters": {"type": "object", "properties": _APP_FIELDS, "required": ["company"]},
}

APPLICATION_UPDATE = {
    "name": "application_update",
    "description": (
        "Change fields of a tracked application, most often its status (e.g. awaiting_confirmation → "
        "applied after submitting, or interview / rejected / offer when the user reports news)."
    ),
    "parameters": {
        "type": "object",
        "properties": {"id": {"type": "integer"}, **_APP_FIELDS},
        "required": ["id"],
    },
}

APPLICATIONS_LIST = {
    "name": "applications_list",
    "description": "List tracked applications, optionally filtered by status or a company/role search.",
    "parameters": {
        "type": "object",
        "properties": {
            "status": {"type": "string", "enum": list(STATUSES)},
            "query": {"type": "string", "description": "Application id, or part of a company/role name"},
        },
    },
}

PROFILE_GET = {
    "name": "profile_get",
    "description": (
        "Get the user's full candidate profile (contact, education, experience, projects, skills, "
        "work authorization, preferences) plus which fields are still missing. Use before filling "
        "an application, tailoring a cover letter, or interview coaching."
    ),
    "parameters": {"type": "object", "properties": {}},
}

PROFILE_UPDATE = {
    "name": "profile_update",
    "description": (
        "Merge new facts into the user's profile. Use when the user tells you something about "
        "themselves, answers a gap-filling question, or pastes a memory export from another AI. "
        "Nested objects merge, lists gain new items, plain values are replaced. Keys follow the "
        "profile shape: contact{name,email,phone,location,address,linkedin,github,website}, "
        "education[], experience[], projects[], skills[], graduation_date, work_authorization, "
        "requires_sponsorship, target_roles[], salary_expectation, availability, eeo{}, resume_path, notes[]."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "updates": {"type": "object", "description": "Partial profile to merge in"},
            "replace": {
                "type": "boolean",
                "description": "Overwrite the given top-level keys instead of merging (to correct mistakes)",
            },
        },
        "required": ["updates"],
    },
}

RESUME_IMPORT = {
    "name": "resume_import",
    "description": (
        "Read a resume file (PDF, DOCX, TXT or MD) the user sent, extract their profile from it, "
        "and merge it into the stored profile. Returns the extracted profile and the fields still "
        "missing, which you should then ask the user for."
    ),
    "parameters": {
        "type": "object",
        "properties": {"file_path": {"type": "string", "description": "Local path of the resume file"}},
        "required": ["file_path"],
    },
}
