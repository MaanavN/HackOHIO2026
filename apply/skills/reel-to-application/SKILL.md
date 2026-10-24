---
name: reel-to-application
description: "Instagram job reel → find the real application page → apply with the user's confirmation."
version: 0.1.0
---

# Reel to application

The user sent an Instagram reel that advertises a job, internship or program, usually with
"comment LINK to get it" and an auto-DM that no longer works. Find the real opportunity and
help them apply. Keep messages short: the user is on their phone.

## 1. Understand the reel

Call `reel_analyze` with the URL.

- If it returns `already_tracked`, tell the user and ask whether to continue.
- If `result.is_opportunity` is false, say what the reel seems to be about and stop.
- If the download fails because Instagram wants a login, tell the user to set the plugin's
  `cookies_file` or `cookies_from_browser` setting with a secondary Instagram account.
- If `result.confidence` is low and `frames_analyzed` is 0, call again with `force_visual: true`.
- The creator's bio often links to the same opportunity. If nothing else works, open
  `uploader_profile_url` with `web_extract` and look for a link-in-bio page.

## 2. Find the official application page

1. Check `result.urls_seen` and the comments first. Open any candidate with `web_extract`.
2. Otherwise run `web_search` with `result.search_queries`.
3. Prefer the company's careers site or its ATS (Greenhouse, Lever, Ashby, Workday, SmartRecruiters)
   over aggregators, news and LinkedIn reposts.
4. Verify the page: right company, right program, and still open. Note the deadline and save the
   full job description text.

If several pages could match, list the top 2–3 and ask the user to pick (`clarify`).

## 3. Save and confirm

Call `application_save` with `company`, `role`, `apply_url`, `reel_url`, `deadline`,
`job_description` and `status: "awaiting_confirmation"`. Then message the user:

> Found: **{company} {role}** → {apply_url}
> Deadline: {deadline or "not stated"}
> Apply now?

Wait for their answer. If they say no, set the status to `skipped`.

## 4. Apply

Call `profile_get`. If required fields are missing, ask for them first and save the answers with
`profile_update`.

Decide the tier from the apply page:

- **Tier 1 (auto-fill):** a Greenhouse, Lever or Ashby form with no account or login.
  Use the browser (`browser_exec`) to fill every field from the profile. Write free-text answers
  and a cover letter tailored to the job description, using only facts from the profile.
  Upload the resume if the form asks and the profile has a resume file path.
  **Before submitting, send the user a summary of every answer and wait for an explicit yes.**
  Submit only after that, then set the status to `applied`.
- **Tier 2 (assisted):** anything that needs an account, a login, a CAPTCHA, or is Workday.
  Never create accounts, enter passwords or solve CAPTCHAs. Send the user the link plus
  ready-to-paste answers for the likely questions and a tailored cover letter. Set the status
  to `assisted`.

## Rules

- Never invent experience, grades or facts that aren't in the profile.
- Never submit anything without the user's explicit confirmation in this conversation.
- Stop and ask if the form asks for something sensitive that isn't in the profile
  (SSN, payment details, government ID): those are for the user to enter themselves.
