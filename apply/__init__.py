"""Apply: a Hermes Agent plugin that turns Instagram job reels into applications.

See SPEC.md at the repository root for the design.
"""

import logging
from pathlib import Path

logger = logging.getLogger(__name__)

TOOLSET = "apply"


def register(ctx):
    from . import commands, host, hooks, schemas, tools

    host.bind(ctx)

    for schema, handler, emoji in (
        (schemas.REEL_ANALYZE, tools.reel_analyze, "🎬"),
        (schemas.APPLICATION_SAVE, tools.application_save, "📌"),
        (schemas.APPLICATION_UPDATE, tools.application_update, "📌"),
        (schemas.APPLICATIONS_LIST, tools.applications_list, "📋"),
        (schemas.PROFILE_GET, tools.profile_get, "👤"),
        (schemas.PROFILE_UPDATE, tools.profile_update, "👤"),
        (schemas.RESUME_IMPORT, tools.resume_import, "📄"),
    ):
        ctx.register_tool(
            name=schema["name"],
            toolset=TOOLSET,
            schema=schema,
            handler=handler,
            description=schema["description"],
            emoji=emoji,
        )

    ctx.register_hook("pre_llm_call", hooks.route)

    for name, handler, description, args_hint in commands.COMMANDS:
        ctx.register_command(name, handler=handler, description=description, args_hint=args_hint)

    skills_dir = Path(__file__).parent / "skills"
    for child in sorted(skills_dir.iterdir()):
        if (child / "SKILL.md").is_file():
            ctx.register_skill(child.name, child / "SKILL.md")

    logger.info("apply plugin registered")
