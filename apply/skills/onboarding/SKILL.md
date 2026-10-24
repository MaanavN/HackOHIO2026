---
name: onboarding
description: "Build the user's candidate profile from a resume, a memory export from another AI, and a few questions."
version: 0.1.0
---

# Onboarding

Goal: a profile complete enough to fill applications and coach interviews.
Check what exists first with `profile_get`.

## From a resume

When the user sends a resume file (PDF, DOCX, TXT or MD), call `resume_import` with its local
path. Then save the path itself so applications can upload it:
`profile_update` with `{"resume_path": "<path>"}`.

Tell the user in two or three lines what you picked up (school, latest role, top skills).

## From another AI's memory

Run or suggest `/import_memory`: it gives the user a prompt to paste into ChatGPT, Gemini or
Claude. When they paste the answer back, turn it into profile fields and save them with
`profile_update`. Anything that doesn't fit a field goes into `notes` as short facts.
Don't overwrite resume facts with vaguer ones from the memory export.

## Fill the gaps

`profile_get` returns `missing.required` and `missing.optional`. Ask for the required ones a
few at a time, in plain words (e.g. "Are you authorized to work in the US, and will you need
visa sponsorship?"). Save each answer with `profile_update`.

Ask about optional fields (address, salary expectation, availability, EEO answers) only once,
and tell the user they can skip any of them. EEO questions are always voluntary.

## Privacy

The profile stays on this machine. Never repeat sensitive details (address, phone, visa status)
back in chat unless the user asks.
