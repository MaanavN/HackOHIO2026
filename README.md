# HackOHIO2026: Apply

Send an Instagram reel about a job or internship to a Telegram bot. It figures out which
opportunity the reel is about, finds the real application page, and helps you apply. It also
works as an interview coach that knows your background. See [SPEC.md](SPEC.md) for the design.

The backend is a [Hermes Agent](https://github.com/NousResearch/hermes-agent) plugin in
[`apply/`](apply). Hermes provides the agent loop, LLM access with your own API keys, the
Telegram gateway, web search and browser tools; the plugin adds the job-specific parts.

## What's in the plugin

| Piece | File | What it does |
|---|---|---|
| Reel pipeline | `apply/reel/` | yt-dlp download → caption, uploader, comments → audio transcript → (if needed) scene-change frames → vision model → structured opportunity |
| Router | `apply/hooks.py` | Spots reel links and resumes in each message and points the agent at the right skill; injects a short profile summary on the first turn |
| Profile | `apply/profile.py`, `apply/resume.py` | Resume import (PDF/DOCX/TXT), memory import, missing-field tracking |
| Tracker | `apply/tracker.py` | SQLite table of applications and their status |
| Tools | `apply/tools.py`, `apply/schemas.py` | `reel_analyze`, `application_save`, `application_update`, `applications_list`, `profile_get`, `profile_update`, `resume_import` |
| Slash commands | `apply/commands.py` | `/jobs`, `/job <company>`, `/setstatus <company> <status>`, `/me`, `/import_memory` |
| Skills | `apply/skills/` | Step-by-step playbooks: `reel-to-application` (find the opportunity and apply with your confirmation), `onboarding`, `interview-coach` |

Finding the application page uses Hermes's built-in `web_search`/`web_extract`, and filling
forms uses its browser tool. The agent always asks before submitting, and never creates
accounts, enters passwords or solves CAPTCHAs: those applications get ready-to-paste answers instead.

## Setup

1. Install ffmpeg:
   ```bash
   brew install ffmpeg
   ```
2. Install Hermes Agent ([docs](https://hermes-agent.nousresearch.com)) and run `hermes setup` to add your LLM API key.
3. Link this plugin into Hermes and enable it:
   ```bash
   ln -s "$PWD/apply" ~/.hermes/plugins/apply
   ```
   ```bash
   hermes plugins enable apply
   ```
4. Let yt-dlp use an Instagram login. Log into a **secondary** Instagram account in a browser, then
   set the plugin's `cookies_from_browser` setting (e.g. `chrome`) under
   `plugins.entries.apply.settings` in `~/.hermes/config.yaml`, or `cookies_file` for a cookies.txt.
5. Set up speech-to-text for transcripts (any Hermes STT provider, e.g. `pip install faster-whisper` for free local transcription).
6. Connect Telegram by following Hermes's Telegram guide, then start the gateway.

Then send the bot your resume, and after that any reel link.

## Local development

```bash
python3 -m venv venv
```
```bash
venv/bin/pip install -r requirements.txt
```
```bash
venv/bin/python -m pytest tests
```

Try the download + frame sampling on a real reel without Hermes (no AI analysis or transcript):

```bash
venv/bin/python scripts/try_reel.py https://www.instagram.com/reel/XXXXXXXX/ --cookies-from-browser chrome
```

Output goes to `data/reels/<id>/`. Inside Hermes, data lives in `~/.hermes/plugin-data/apply/`
(`apply.db`, `profile.json`, `reels/`), never in this repo.
