"""pre_llm_call hook: the router (SPEC §2).

Hermes appends whatever this returns to the current user message, so it is how
the agent learns which workflow a message needs without changing the system prompt.
"""

import logging
import re

from . import profile
from .reel.download import find_reel_urls

logger = logging.getLogger(__name__)

_RESUME_RE = re.compile(r"\b(resume|résumé|cv)\b|\.(pdf|docx)\b", re.I)

_REEL_HINT = (
    "[apply] The user sent an Instagram reel link: {urls}. Load the skill "
    "`apply:reel-to-application` with skill_view and follow it."
)
_RESUME_HINT = (
    "[apply] If the user just sent a resume file, load the skill `apply:onboarding` with "
    "skill_view and follow it."
)
_NO_PROFILE_HINT = (
    "[apply] The user has no candidate profile yet. When it fits the conversation, offer to set "
    "one up (skill `apply:onboarding`)."
)
_COACH_HINT = (
    "[apply] For interview prep, resume or cover-letter questions, load the skill "
    "`apply:interview-coach` with skill_view."
)


def _text_of(message) -> str:
    """The user message may be a string or a list of multimodal content parts."""
    if isinstance(message, str):
        return message
    if isinstance(message, list):
        return " ".join(p.get("text", "") for p in message if isinstance(p, dict))
    return ""


def route(user_message="",is_first_turn: bool = False, **kwargs):
    try:
        message = _text_of(user_message)
        parts = []

        urls = find_reel_urls(message)
        if urls:
            parts.append(_REEL_HINT.format(urls=", ".join(urls)))

        if _RESUME_RE.search(message):
            parts.append(_RESUME_HINT)

        if is_first_turn:
            summary = profile.summary()
            if summary:
                parts.append("[apply] What you know about the user (full profile: profile_get):\n" + summary)
                parts.append(_COACH_HINT)
            else:
                parts.append(_NO_PROFILE_HINT)

        return {"context": "\n\n".join(parts)} if parts else None
    except Exception:
        logger.exception("apply router hook failed")
        return None
