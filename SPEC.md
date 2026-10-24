# Apply — Spec

An AI agent you message with Instagram reel links. It figures out which job/internship opportunity the reel is about, finds the real application page, and applies for you. It also doubles as an interview coach that knows your profile.

## Problem

Many Instagram reels advertise opportunities with "comment LINK to get the application." The auto-DM that sends the link usually stops working after a while, so people comment and never get it. Apply recovers the opportunity from the reel itself and handles the application.

## Scope

- **Input source:** Instagram reels only.
- **Users:** single user (the owner) for v1. Multi-user is a later phase.
- **LLM calls:** use the user's own API keys (Claude / OpenAI / Gemini).
- **Backend:** built on [Hermes Agent](https://github.com/NousResearch/hermes-agent), reusing its tools, memory, and messaging gateway.
- **Messaging:** Telegram for v1 (supported by the Hermes gateway, handles files and links, free). SMS via AWS End User Messaging is a later phase.

## Architecture

```
Telegram ──► Hermes gateway ──► Router
                                  ├─ Instagram reel URL ──► Reel pipeline ──► Opportunity resolver ──► Apply engine ──► Tracker
                                  ├─ File upload (resume) ─► Profile builder
                                  ├─ /command ────────────► Tracker / profile commands
                                  └─ Anything else ───────► Chat / interview coach (uses profile + tracker)
                                                                              │
                                              all results messaged back ◄─────┘
```

## Components

### 1. Profile

Everything the agent knows about the user, stored as `profile.json` and loaded into Hermes memory.

- **Resume upload:** user sends a PDF/DOCX. The agent parses it into structured fields: contact, education, experience, projects, skills, links.
- **Memory import:** the bot gives the user a prompt to paste into ChatGPT/Gemini/Claude ("List everything you know about me as a job candidate…"). The user pastes the answer back and it's merged into the profile.
- **Gap filling:** the agent asks for fields applications need that are still missing: address, work authorization/visa, graduation date, salary expectations, EEO answers, availability.

### 2. Router

Classifies each incoming message:

| Input | Route |
|---|---|
| `instagram.com/reel/…` or `/p/…` URL | Reel pipeline |
| File attachment | Profile builder |
| `/command` | Command handler |
| Anything else | Chat / interview coach |

### 3. Reel pipeline

Downloads the reel and extracts two kinds of information.

**Download:** `yt-dlp`, with cookies from a secondary Instagram account. Saves the video plus `info.json`.

**A. Metadata (runs first, cheap)**
- Caption
- Uploader handle, bio, and bio link (linktree etc.)
- Top comments (other users often post the real link)
- Upload date (to judge if the opportunity is still open)
- Audio transcript: `ffmpeg` extracts audio → Whisper

**B. Visual information (runs if metadata isn't conclusive)**
- Sample frames with ffmpeg scene detection (`select='gt(scene,0.3)'`) or 1 fps, then drop near-duplicates. Target 5–20 frames.
- OCR each frame for on-screen text (company names, program names, deadlines, URLs).
- Send the frames in one vision-model call to identify logos, screenshots of application pages, URLs in the background, and company branding.
- Alternative: send the whole video to Gemini, which handles audio + visuals natively. Benchmark against the frame pipeline.

**Output:** the LLM merges A + B into one structured result:

```json
{
  "company": "Google",
  "program": "STEP Internship 2027",
  "role_type": "internship",
  "deadline": "2026-11-01",
  "urls_seen": ["..."],
  "confidence": 0.85,
  "evidence": "caption + transcript + OCR on frame 4"
}
```

### 4. Opportunity resolver

- Web-search using the extracted fields to find the official application page (prefer the company careers site or ATS over aggregators).
- Verify the page matches (company, program, still open).
- Reply to the user: *"Found: Google STEP Internship 2027 → <link>. Deadline Nov 1. Apply?"*
- If confidence is low, show the top candidates and ask the user to pick one.

### 5. Apply engine

Uses Hermes browser tools. Always sends a preview and waits for the user's confirmation before submitting.

- **Tier 1, auto-fill and submit:** forms that don't need an account (Greenhouse, Lever, Ashby).
- **Tier 2, assisted:** Workday, forms that need logins or account creation, or forms with CAPTCHAs. The agent sends the link plus ready-to-paste answers and a tailored cover letter; the user submits.
- Tailors free-text answers and cover letters to the job description using the profile.

### 6. Tracker

SQLite table `applications`:

| Column | Notes |
|---|---|
| id | |
| reel_url | source reel |
| company, role | |
| apply_url | |
| deadline | |
| status | `found` → `awaiting_confirmation` → `applied` / `assisted` / `skipped` → `interview` / `rejected` / `offer` |
| job_description | saved for interview prep |
| created_at, updated_at | |

Telegram commands:

- `/jobs`: list applications and their status
- `/status <company>`: details for one application
- `/update <company> <status>`: change a status manually
- `/profile`: show the stored profile
- `/resume`: upload or replace the resume

### 7. Interview coach

Chat mode with the profile and the tracker's job descriptions in context:

- Mock interviews (behavioral and technical) for a specific saved application
- STAR-format feedback on answers
- Company research summaries
- Resume and cover letter feedback

## Tech stack

- Python 3.11+
- Hermes Agent (agent loop, tools, memory, Telegram gateway)
- `yt-dlp` for downloads, `ffmpeg` for audio and frames
- Whisper (local or API) for transcription
- An OCR library plus a vision LLM (or Gemini for whole-video input)
- SQLite for tracking
- Hosting: a small VPS or AWS EC2; secrets in environment variables

## Milestones

1. **Reel download:** a script downloads a reel and prints its metadata (caption, uploader, date, comments).
2. **Reel understanding:** transcript + frame sampling + OCR + vision produce the structured result above.
3. **Opportunity resolver:** structured result → verified application link.
4. **Hermes + Telegram:** a reel URL sent to the bot gets back the found opportunity.
5. **Profile:** resume parsing, memory import, gap filling.
6. **Apply engine:** Tier 2 (assisted) first, then Tier 1 auto-submit with confirmation.
7. **Tracker and commands.**
8. **Interview coach.**
9. **Deploy:** always-on server, logging.
10. **Later:** AWS SMS channel, multiple users with their own keys, deadline reminders.

## Risks and constraints

- **Instagram downloads are fragile:** they need login cookies, are rate-limited, and break when Instagram changes. Scraping is against Instagram's terms of service. Use a secondary account, never the main one.
- **The link is usually not in the video:** the pipeline's job is to identify the opportunity, then search for it.
- **CAPTCHAs and account creation** are left to the user (Tier 2).
- **Personal data:** the profile holds sensitive information (address, visa status). Keep it local, out of git, and out of logs.
- **Cost:** vision and transcription calls add up. Run the metadata stage first and skip the visual stage when metadata is conclusive.

## Open questions

- Telegram vs. SMS for v1 (this spec assumes Telegram).
- Gemini whole-video input vs. the frame pipeline: decide after benchmarking on about 20 real reels.
- How much to auto-submit vs. always use assisted mode.
