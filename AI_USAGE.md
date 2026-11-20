# AI usage

I built this project with AI help and kept the parts I must be able to explain in my own hands. This file says which tool did what, shows prompts that mattered, lists mistakes the AI made and how I caught them, and separates what I wrote from what I did not. `AI_SESSIONS.json` has the per-session details.

## Tools and models

| Session | Tool | Model shown in the tool | Used for |
|---|---|---|---|
| S1 | Claude (web) | Claude Sonnet 5.5 (medium) | Mentor: foundation, config, DB model, AI schema, mock provider, parser spec, Groq client |
| S2 | Antigravity | gemini-3.8-flash-high | Templates, CSS, public routes, route tests |
| S3 | Gemini (web) | Hydrogen (medium) | analyze_story orchestrator, 69-test validation specification |
| S4 | Claude (web) | Claude Sonnet 5.5 (medium) | Admin login, session cookie, CSRF override, admin tests, review of everything |
| S5 | Antigravity | gemini-3.8-flash-high | Documentation first drafts, test 8 upgrade, secrets scan |

**Logs.** S1, S3 and S4 are web chats, so `AI_SESSIONS.json` holds their share links instead of exported files. S2 and S5 are in `ai-logs/` as copies of the Antigravity conversations, not edited.

## What I wrote by hand

- `app/ai/parse.py`: the AI response parser. I wrote the tests first and watched them fail. The first version was reviewed in S1, which found that `from exc` left story text in tracebacks and that `json.loads` can raise `RecursionError`; I fixed both.
- `tests/test_parse.py`: 30 tests, including the broken-response and wrong-values cases, a traceback leak test, and a deliberate sabotage check.
- `app/validation.py`: server-side validation and contact normalisation, written against the 69 tests Gemini generated in S3.
- `tests/test_security.py`: 14 tests for the credential check, login limiter and CSRF check.

## What AI wrote that I kept or changed

- `tests/test_validation.py` (69 tests): generated in S3 as a specification. I wrote `validation.py` to pass it.
- `app/security.py`, `app/admin.py`, admin templates: drafted in S4. I explained each part back in the chat, then ran and tested it.
- `tests/test_admin.py` (16 tests): written to a table of cases from S4. Test 8 was later changed by Antigravity in S5 so it also sends a cookie made with itsdangerous and a different key. That proves forged cookies are rejected, but it is not a byte-exact copy of Starlette's own cookie format.
- Templates and CSS: S2. The public wall and copy were corrected after review (`d637bce`, `d5a36c7`, `949a0c4`).
- Config, DB model, mock provider, AI schema, Groq client: S1 drafts. I changed the model name, removed `response_format` and raised `max_tokens` after live runs.

## Prompts that mattered

**1. S1, the opening prompt (Claude).** Excerpt; the full text is in the S1 share link.

> You are my pair-programming mentor for a hiring take-home assignment. I must be able to explain every line of this project and make a small live change in 15 minutes on a review call, so teach as you build: keep the code simple, explain each file in plain words, and make me write the most important parts myself. [...] START by confirming you understand, then ask any questions you need before proposing the structure.

Why it mattered: it set the rule that I write the parser, its tests and the validation by hand, and that every step ends with a command I run.

**2. S2, the public flow prompt (Antigravity).** Excerpt; full text in `ai-logs/S2-antigravity.md`.

> `story` (with live JS character counter `0 / 2000` ...) [...] Displays a curated "Approved #MyChaiBreak Stories" wall ... (displaying `ai_caption`, `story`, `name`, and `city` ...)

Why it mattered: it worked, but my own prompt contained two errors. The brief says 300 characters, and my privacy rule says the public wall shows only first name and caption. Both were caught in review and fixed.

**3. S3, the validation specification (Gemini).**

> Following my rule that I write `app/validation.py` by hand: generate a comprehensive pytest suite `tests/test_validation.py` first as a TDD specification covering name, city, email vs Indian/E.164 phone normalisation, trimming, multi-field error aggregation, 300-character story limit, and explicit consent=True. Do not write `app/validation.py` yet - just give me the tests and spec so I can implement it myself and run pytest against it.

Why it mattered: it gave me a test-first target for the one file I most wanted to own.

**4. S5, the documentation prompt (Antigravity).** Excerpt; full text in `ai-logs/S5-antigravity.md`.

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
| S3 | Generated validation tests named and commented the limit as 2000 and built stories from `MAX_STORY_LENGTH`, so they passed with the wrong value; the 2000 was also in my own `validation.py` | Claude review against the brief; fixed in `d637bce` |
| S4 | Predicted that removing the CSRF check would fail tests 9 and 13/14; only 9 can | I ran the sabotage |
| S4 | Spec to walk `app.routes` found zero routes in FastAPI 0.163.1 | The `checked >= 2` assertion failed |
| S5 | README listed mock triggers that do not exist and `AI_PROVIDER=groq`, which `config.py` rejects | Claude compared it with the code |
| S5 | Docs listed `ai_error` codes the code never writes and said `ai_decision` is "rejected" on AI failure; it is empty | Claude compared it with `analyze_story()` |
| S5 | Paraphrased text was labelled "verbatim" prompts; `ai-logs/` held summaries; `test_admin.py` was called fully hand-written | Claude review; corrected in this file |

## What I rejected

- Installing `httpx2`, which a Starlette deprecation warning suggested.
- Summary files in `ai-logs/` presented as exports.

## Honest limits

- Prompt injection is reduced by the schema and the admin override, not eliminated.
- Real-AI testing was one 5-story run plus a few manual submissions on a phone. It is not a benchmark.