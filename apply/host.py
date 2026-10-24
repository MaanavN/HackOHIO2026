"""Access to the Hermes plugin context, with fallbacks for running outside Hermes.

register(ctx) stores the context here so tool handlers can reach ctx.llm and
plugin settings. Local scripts never call register, so llm() returns None and
setting() falls back to APPLY_<KEY> environment variables.
"""

import os

_ctx = None


def bind(ctx) -> None:
    global _ctx
    _ctx = ctx


def llm():
    return getattr(_ctx, "llm", None)


def setting(key: str, default=None):
    if _ctx is not None:
        try:
            value = _ctx.get_config(key, default=None)
            if value not in (None, ""):
                return value
        except Exception:
            pass
    return os.environ.get(f"APPLY_{key.upper()}", default)
