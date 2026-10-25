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
The tool always watches sampled video frames and uses an audio transcript when available.
Do not fetch Instagram profiles or comments. Use visible or spoken application URLs and the
identified opportunity to proceed to the official site.

## 2. Find the official application page

1. Check `result.urls_seen` first. Open any candidate with `web_extract`.
2. Otherwise run `web_search` with `result.search_queries`.
3. Prefer the company's careers site or its ATS (Greenhouse, Lever, Ashby, Workday, SmartRecruiters)
   over aggregators, news and LinkedIn reposts.
4. Verify the page: right company, right program, and still open. Note the deadline and save the
   full job description text.

If several pages could match, list the top 2–3 and ask the user to pick (`clarify`). If
`result.confidence` is still below ~0.75 after visual analysis, say what the reel seems to
advertise, show the best candidates, and ask which one before saving anything.

## 3. Save the opportunity

Call `application_save` with `company`, `role`, `apply_url`, `reel_url`, `deadline`,
`job_description` and `status: "found"`. Continue to the application using the user's existing
instruction to apply on their behalf. Ask for authorization only if it has not already been given.

## 4. Apply

Call `profile_get`. If required fields are missing, ask for them first and save the answers with
`profile_update`.

Decide the tier from the apply page:

- **Tier 1 (auto-fill):** a Greenhouse, Lever or Ashby form with no account or login.
  Use the browser (`browser_exec`) to fill every field from the profile. Write free-text answers
  and a cover letter tailored to the job description, using only facts from the profile.
  Upload the resume if the form asks and the profile has a resume file path.
  When the user has authorized applying on their behalf, submit the completed application.
  Otherwise show a summary of the answers and ask for authorization. Verify the submission
  confirmation before setting the status to `applied`.
- **Tier 2 (assisted):** anything that needs an account, a login, a CAPTCHA, or is Workday.
  Never create accounts, enter passwords or solve CAPTCHAs. Send the user the link plus
  ready-to-paste answers for the likely questions and a tailored cover letter. Set the status
  to `assisted`.

## 5. Tell the user you're done

The user is on their phone, so report the outcome in a few lines as soon as the work is finished:

> Applied to **{company} — {role}** ✅
> {apply_url}
> Saved as `applied` in your tracker. Want me to prep you for the interview?

For Tier 2, say the link and answers are ready and ask them to tell you once they've submitted,
then update the status to `applied`. Never claim you applied when you only prepared the answers.

## 6. Clean up

Once you're finished with the reel — applied, assisted, skipped, or not an opportunity — call
`reel_cleanup` with its URL. That deletes the downloaded video, extracted audio, sampled frames
and cached analysis from disk. The tracker entry and its `reel_url` stay, so `/jobs` still works.

## Rules

- Never invent experience, grades or facts that aren't in the profile.
- Honor the user's existing authorization to apply; do not request it again for each step.
- Call `reel_cleanup` before your final reply about a reel, including when you skip it or it
  turns out not to be an opportunity.
- Stop and ask if the form asks for something sensitive that isn't in the profile
  (SSN, payment details, government ID): those are for the user to enter themselves.
