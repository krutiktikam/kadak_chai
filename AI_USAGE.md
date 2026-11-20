# AI usage

I built this project with AI help. This file says which tool did what, shows prompts that mattered, lists mistakes the AI made and how I caught them, and separates what I wrote from what I did not. `AI_SESSIONS.json` has the per-session details.

## Tools and models

| Session | Tool | Model shown in the tool | Used for |
|---|---|---|---|
| S1 | Claude (web) | Claude Sonnet 5.5 (medium) | Mentor: foundation, config, DB model, AI schema, mock provider, parser spec, Groq client |
| S2 | Antigravity | gemini-3.8-flash-high | One thread, 17-20 Nov: saved and ran code from the Claude chats, wrote `validation.py`, templates, CSS, route and admin tests, first drafts of the documents |
| S3 | Gemini (web) | Hydrogen (medium) | `analyze_story` orchestrator, 69-test validation specification |
| S4 | Claude (web) | Claude Sonnet 5.5 (medium) | Admin login, session cookie, CSRF override, admin test specs, review of everything |

**Logs.** S1, S3 and S4 are web chats, so `AI_SESSIONS.json` holds their share links. `ai-logs/S2-antigravity.jsonl` is the raw Antigravity transcript, copied from the tool's own history (one continuous thread, 667 steps). I replaced one Groq API key in it with `[REDACTED]` and changed nothing else. The steps are:

| Steps | Date (UTC) | What happened |
|---|---|---|
| 0-58 | 17 Nov | Fixed the Groq client |
| 59-230 | 17 Nov | Public flow, templates, `validation.py` |
| 231-448 | 18 Nov | Saved the admin code from S4, wrote admin tests |
| 449-559 | 19 Nov | First drafts of the documents, test 8 upgrade |
| 560-667 | 20 Nov | The 300-character test and the log extraction |

## What I wrote by hand

- `app/ai/parse.py`: the AI response parser. I wrote the tests first and watched them fail. S1 reviewed it and found that `from exc` left story text in tracebacks and that `json.loads` can raise `RecursionError`; I fixed both.
- `tests/test_parse.py`: 30 tests, including the broken-response and wrong-values cases, a traceback leak test, and a deliberate sabotage check.

Everything else was written or saved by an AI tool. I went through the Python files with Claude and explained them back, but I did not type them.

## What AI wrote, and what I did with it

- **`app/validation.py`:** written by Antigravity (S2, step 92) from a rule checklist I gave it, against the 69 tests Gemini generated in S3. An earlier commit message (`727dc77`) and an early draft of this file called it hand-written. That was wrong, and I found it by reading the raw Antigravity log.
- **`tests/test_validation.py`:** generated in S3 as a specification, later edited by Antigravity (300-character limit and the test that pins it).
- **`tests/test_security.py`:** tests/test_security.py: 14 unit tests for check_credentials, LoginLimiter, and csrf_ok, written by hand against the Phase 4 security rules.
- **`tests/test_admin.py`:** written by Antigravity from a table of cases from S4. Test 8 was changed by Antigravity so it also sends an itsdangerous cookie made with a different key. That proves forged cookies are rejected, but it is not a byte-exact copy of Starlette's own cookie format.
- **`app/security.py`, `app/admin.py`, admin templates:** drafted in S4 and saved by Antigravity. I ran them, tested them and explained them back in the chat.
- **Templates and CSS:** S2. The public wall and copy were corrected after review (`d637bce`, `d5a36c7`, `949a0c4`).
- **Config, DB model, mock provider, AI schema, Groq client:** S1 drafts. I changed the model name, removed `response_format` and raised `max_tokens` after live runs.

## Prompts that mattered

**1. S1, the opening prompt (Claude).** Excerpt; the full text is in the S1 share link.

> You are my pair-programming mentor for a hiring take-home assignment. I must be able to explain every line of this project and make a small live change in 15 minutes on a review call, so teach as you build: keep the code simple, explain each file in plain words, and make me write the most important parts myself. [...] START by confirming you understand, then ask any questions you need before proposing the structure.

Why it mattered: it set the rule that I write the parser and its tests by hand, and that every step ends with a command I run.

**2. S2, the public flow prompt (Antigravity, step 99).** Excerpt; the full text is in `ai-logs/S2-antigravity.jsonl`.

> `story` (with live JS character counter `0 / 2000` ...) [...] Displays a curated "Approved #MyChaiBreak Stories" wall ... (displaying `ai_caption`, `story`, `name`, and `city` ...)

Why it mattered: it worked, but my own prompt contained two errors. The brief says 300 characters, and my privacy rule says the public wall shows only first name and caption. Both were caught in review and fixed.

**3. S3, the validation specification (Gemini).**

> Following my rule that I write `app/validation.py` by hand: generate a comprehensive pytest suite `tests/test_validation.py` first as a TDD specification covering name, city, email vs Indian/E.164 phone normalisation, trimming, multi-field error aggregation, 300-character story limit, and explicit consent=True. Do not write `app/validation.py` yet - just give me the tests and spec so I can implement it myself and run pytest against it.

Why it mattered: it gave me a test-first target. In the end I did not implement `validation.py` by hand: I gave Antigravity a rule checklist (S2, step 91) and it wrote the file.

**4. S2, the documentation prompt (Antigravity, step 449).** Excerpt.

> Complete Step 2 (test upgrade, local log extraction, secrets scan) and Step 3 (documentation generation) ... Create `ai-logs/` with four UTF-8 Markdown files ...

Why it mattered: it produced documents with factual errors and log files that were summaries, not exports. I caught that in review and removed them (see the table).

## Mistakes the AI made and how I caught them

| Session | What went wrong | How it was caught |
|---|---|---|
| S1 | The parser spec let exception chains carry story text into tracebacks | A review comment, then a traceback assertion that failed before the fix |
| S1 | Suggested Groq model names that returned 404 | Live call, then the provider's `/models` list |
| S1 | `response_format: json_object` returned 400 | Live call |
| S1 | `max_tokens: 200` truncated a reasoning model's JSON | A live run produced `invalid_json` from my parser |
| S2 | My prompt asked for a 2000-character counter and for story and city on the public wall, against the brief and my privacy rule | Claude review against the brief; fixed in `d637bce` |
| S2 | `index.html` said every entry is reviewed before publication and promised limited-edition tea tins | Claude review; fixed in `d5a36c7` and `949a0c4` |
| S2 | First README listed mock triggers that do not exist and `AI_PROVIDER=groq`, which `config.py` rejects | Claude compared it with the code |
| S2 | First documents listed `ai_error` codes the code never writes and said `ai_decision` is "rejected" on AI failure; it is empty | Claude compared it with `analyze_story()` |
| S2 | Paraphrased text was labelled "verbatim" prompts and `ai-logs/` held summaries | Claude review; removed |
| S2 | `validation.py` was described as hand-written, but Antigravity wrote it | I read the raw log against my claims; corrected here |
| S2 | Antigravity read `.env` and printed a real API key into its transcript | I scanned the log before committing; redacted it and rotated the key |
| S2 | Antigravity copied one transcript into two files and presented them as two sessions | Compared checksums; kept one |
| S3 | Generated validation tests named the limit as 2000 and used the `MAX_STORY_LENGTH` constant, so they passed with the wrong value; the 2000 was also in `validation.py` | Claude review against the brief; fixed in `d637bce` |
| S4 | Predicted that removing the CSRF check would fail tests 9 and 13/14; only 9 can | I ran the sabotage |
| S4 | Spec to walk `app.routes` found zero routes in FastAPI 0.163.1 | The `checked >= 2` assertion failed |

## What I rejected

- Installing `httpx2`, which a Starlette deprecation warning suggested.
- Summary files in `ai-logs/` presented as exports.

## Honest limits

- Most of the code was written or saved by AI tools. My own hand-written part is the parser and its tests.
- Prompt injection is reduced by the schema and the admin override, not eliminated.
- Real-AI testing was one 5-story run plus a few manual submissions on a phone. It is not a benchmark.