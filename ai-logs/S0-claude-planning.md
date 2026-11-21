# S0 - Claude (web) planning chat, selected replies

This is not a full export. It holds two replies from the chat where I planned the project, copied as written. My own messages in that chat and its unrelated replies are left out, and one section of the first reply is replaced by `[removed: unrelated]`. The chat is not shared as a link because it also holds personal material. Nothing else was edited.

Date: 17 Nov 2026 (IST). Used for: reading the brief, choosing the stack, the timeline, and the opening prompt I pasted into the build chat (S1).

---

## Reply 1 - the plan

# Congratulations, and the plan

Passing the interview and getting a take-home is a real step forward. This is now your top priority. I've broken the assignment down below and set a timeline that ends with your submission on **Sunday morning**, not at the 6:00 PM deadline.

## What the assignment is

You build a campaign microsite for a fictional brand, Kadak Chai Co., for a campaign called **#MyChaiBreak**:
- People submit a short chai-break story through a **mobile-first** form.
- A backend sends each story to an **LLM**, which returns structured JSON: `decision` (approved or rejected), `reason`, `category` (funny, nostalgic, wholesome, other) and `caption` (12 words or fewer).
- Approved entries get a shareable result page. The brand team reviews everything in an **admin dashboard**.

**Time and deadline.** The brief expects 10-12 hours of work. Your email says to submit by **Sunday, Nov 22, 6:00 PM**, through a Google form (repo link, live link if any, AI tools used, hours spent).

## The six required items (do these first)

| # | Required | What "done" looks like |
|---|---|---|
| 1 | **Landing page and form** | Mobile-first. Fields: name, city, email or phone, story (300 characters max), consent checkbox. Validation on the client **and on the server**, because they'll call your API directly |
| 2 | **Backend and database** | Any database. Store each entry with its status and the AI output |
| 3 | **AI step** | Story goes to an LLM; response is validated against a schema before saving. On timeout, error, bad JSON or wrong values: save as `pending_review`, don't crash, and show the user no technical error. **`AI_PROVIDER=mock` must work with no API key** and return predictable output. Real AI uses a free option (Groq, OpenRouter free models, Gemini free tier or local Ollama), configured by `AI_BASE_URL`, `AI_API_KEY`, `AI_MODEL`. Treat a rate-limit error as any other failure |
| 4 | **Result page** | Shows the person's **first name** and the caption. URLs must not be guessable (no `/entry/1`) |
| 5 | **Admin dashboard** | Login (username and password from environment variables), list entries, filter by status, override the AI's decision |
| 6 | **Tests** | Real tests for the code that parses the AI response: a broken response, and a valid-looking one with wrong values |

## Required documents

- **README.md:** how to run locally in **under 10 minutes**, env vars, your decisions and why, what's unfinished, and roughly how many hours you spent. Write assumptions here (the brief invites this).
- **AI_USAGE.md** (read closely): tools and models used and for which parts; **3-5 real prompts that mattered**; **at least 2 times the AI got something wrong and how you caught it**; which parts you wrote by hand.
- **AI_SESSIONS.json and `ai-logs/`:** exported chats from every AI tool you used, numbered S1, S2 and so on, in the format in the brief. Redact API keys and passwords, don't tidy the logs, and cut only unrelated personal content, marked `[removed: unrelated]`.
- **.env.example** with no real keys. They check the **full git history** for secrets.
- **Public GitHub repo** with commits made as you go (no squashing at the end). When one session produced most of a commit, add its id, like `feat: entry API [S2]`.
- Optional: live link, 3-5 minute screen recording.

## Nice-to-have (only after the six work)

Live deployed link, per-IP rate limiting and duplicate email/phone blocking, CSV export and a category filter, poster-style result design, an Open Graph image for sharing, a Hindi toggle, Docker. **My order if time allows:** live link, then abuse protection, then CSV export and category filter. Skip Hindi and Docker unless you finish early.

## How they'll score it

| Area | Weight |
|---|---|
| Core flow works end to end | 25 |
| Code quality and structure | 20 |
| AI integration (structured output, validation, failure handling, mock mode) | 20 |
| Security and edge cases | 15 |
| UI and mobile experience | 10 |
| README, AI_USAGE.md, AI logs, honesty | 10 |

**Read this as a strategy:** 80% of the score is the working flow, code quality, AI handling and security. Only 10% is design. A plain, solid app beats a pretty, fragile one.

## The review call (45 minutes)

You'll share your screen, explain your choices, say where AI helped or misled you, and make **a small live change in about 15 minutes**. Code you can't explain hurts you more than a missing feature does. So build in a way you can explain, and rehearse small changes like adding a category or changing the caption limit.

## Choose your stack tonight (15 minutes, then stop deliberating)

| Option | Good | Risk |
|---|---|---|
| **A. FastAPI + React (TypeScript)** | You know both | Two services to wire, and social-sharing previews need server-rendered HTML anyway |
| **B. Next.js + TypeScript** | Matches their stack, one deployment, easy sharing image | Least familiar to you; risky to explain and change live |
| **C. FastAPI + server-rendered pages (Jinja2 templates) with a little JavaScript** | Fewest moving parts, easiest to explain and modify live, the result page is real HTML so sharing previews work, one deployment | Less React to show off |

**My recommendation: C**, unless you're genuinely quick in Next.js. Design is only 10% of the score, and you'll be asked to change code live. Use SQLite locally through SQLAlchemy and a `DATABASE_URL` env var, so a free hosted Postgres works if you deploy (free hosts often lose local files on restart).

## Design decisions to settle early

- **Data model:** internal id, a random `public_id` (for example from `secrets.token_urlsafe`), name, city, contact (normalised, with a unique index if you do duplicate blocking), story, consent plus timestamp, status (`approved`, `rejected`, `pending_review`), the AI decision, reason, category and caption, an error note if the AI failed, and created and reviewed times.
- **AI module:** one function takes the story and returns a validated result. A Pydantic model enforces enums, the 12-word caption limit and "reason required if rejected." Any exception, timeout, rate limit or invalid result becomes `pending_review`. Log the error type, not the story.
- **Mock provider:** deterministic rules (for example spam words give a rejection; keywords choose the category; the caption is fixed) so the tests and reviewers get the same output every run.
- **Prompt injection:** the story is untrusted input. Tell the model to treat it as data, and rely on schema validation, not on the prompt, for safety.
- **Public pages:** only approved entries are visible. Non-approved entries and unknown ids return 404. Show the first name and the caption only, never email, phone or city.
- **Admin:** credentials from env vars, constant-time comparison, a signed session cookie, login attempt limits, and a CSRF protection or `SameSite=Strict` cookies for the override action.
- **Server validation:** story length, contact format, consent must be true, trimmed inputs, and escaped output.

## Timeline (all times IST)

Today is Tuesday, Nov 17, and the email came at 6:10 PM.

| When | Work | Hours |
|---|---|---|
| **Tue Nov 17, tonight (45-60 min, then sleep)** | Read the brief once fully; choose the stack; open a new, dedicated AI session; create the repo; write `.env.example` and the README skeleton; get a free API key (Groq or Gemini) and test it with one request; write your assumptions list | ~1 |
| **Wed Nov 18: foundation** | 7:10-8:40: project skeleton, config, DB model, the entry endpoint with server validation. 10:15-11:45: the AI module (schema, prompt, mock provider, real provider, timeouts, failure handling) plus parser tests. 3:00-4:30: full flow end to end (submit, AI, save) | ~5 |
| **Thu Nov 19: UI and admin** | 7:10-8:40: landing page and form, mobile-first, client validation, friendly messages for every outcome. 10:15-11:45: result page and unguessable URLs. 3:00-4:30: admin login, list, status filter, override | ~5 |
| **Fri Nov 20: harden and test** | Hit the API directly with bad inputs; more tests; try the real provider and handle rate limits; run from a clean clone in mock mode; check mobile on a real phone; secret scan | ~4-5 |
| **Sat Nov 21: documents and extras** | README, AI_USAGE.md, AI_SESSIONS.json, export and redact logs, git history check; then the best nice-to-haves (deploy, abuse protection, CSV and category filter) | ~4 |
| **Sun Nov 22: submit** | Morning: final check from a fresh clone, repo public, links work. **Submit by about noon.** Afternoon: rehearse the review call | ~2 |

That's about 20 hours of available time against an expected 10-12, so you have buffer. **Don't use all of it:** finish the core by Thursday night, and treat Friday and Saturday as hardening and documentation.

## What to pause this week

[removed: unrelated]

## Rules for working with AI on this

- **Log as you go.** After each important prompt, copy it to a running file. Note each time the AI got something wrong the moment you catch it. Real ones are common: a library function that doesn't exist, weak validation, guessable ids, missing server checks, leaked keys.
- **Use a dedicated chat or tool for the build,** and export it. Don't use this long chat for the code, because it holds unrelated personal material and you can't cut it cleanly.
- **This planning conversation counts as AI use.** Save my plan above into `ai-logs/S0-claude-planning.md` and mark everything unrelated as `[removed: unrelated]`. List it in `AI_SESSIONS.json` and mention it in `AI_USAGE.md`.
- **Read and understand every file** the AI produces before you commit it. Rewrite the parts you can't explain. Write the AI parser and its tests mostly by hand, since that's what they'll probe.
- **Commit small and often,** with session ids in the messages. Never commit a `.env` file, and scan the history before the repo goes public.

## Next step

Tell me which stack you choose. Then I'll give you a prompt for the dedicated build chat, with the requirements, your rules and a first-session plan.

---

## Reply 2 - the stack decision and the build-chat prompt

# Option C is locked in

A single FastAPI app with server-rendered pages is the right call for this assignment. It has the fewest moving parts, it's the easiest to explain on the review call, and the result page is plain HTML, which also makes sharing previews easy later.

Below is the prompt for a **new, dedicated chat or tool**, used only for building this project. Keep it separate from this chat so you can export a clean log. Use a tool that can export its sessions: Claude Code (`/export`), Cursor (Export Chat), Gemini CLI (`/chat share`), or Claude on the web (a Share link). Paste the assignment text into that chat too, as its first message after the prompt.

## Prompt for the build chat

```
You are my pair-programming mentor for a hiring take-home assignment. I must be able to explain every line of this project and make a small live change in 15 minutes on a review call, so teach as you build: keep the code simple, explain each file in plain words, and make me write the most important parts myself.

=== THE ASSIGNMENT (summary; I will paste the full brief) ===
Company: Ecultify Advertising LLP. Role: AI-First Full Stack Developer. Fictional brand: Kadak Chai Co. Campaign: #MyChaiBreak. People submit a short chai-break story; an AI checks each entry, tags it, and writes a one-line poster caption; approved entries get a shareable page; the brand team reviews everything in an admin dashboard.
Deadline: Sunday 22 Nov 2026, 6:00 PM IST, via a submission form (I aim to submit by noon). About 10-12 hours of effort.

REQUIRED (build and finish these first):
1. Landing page and entry form. Mobile first. Fields: name, city, email OR phone, story (300 characters max), consent checkbox. Validate on the client AND on the server (they will hit the API directly).
2. Backend and database. Store each entry with its status and the AI output.
3. AI step. On submit, the backend sends the story to an LLM and gets structured JSON: decision (approved | rejected; off-topic, abusive or spam stories are rejected), reason (why, if rejected), category (funny | nostalgic | wholesome | other), caption (12 words or fewer). Validate against a schema BEFORE saving. On timeout, error, invalid JSON, wrong values or a rate limit: save the entry as pending_review, do not crash, and show the user no technical error. AI_PROVIDER=mock must work with no API key and return predictable output (they run mock mode first). Real AI uses a free provider (Groq, OpenRouter free models, Gemini free tier or local Ollama) through env vars AI_BASE_URL, AI_API_KEY, AI_MODEL. If no free key works, mock alone is acceptable (say so in the README).
4. Result page. Each approved entry gets a page showing the person's first name and the caption. URLs must not be guessable (no /entry/1).
5. Admin dashboard. Login with a username and password from environment variables; list entries; filter by status; override the AI's decision.
6. Tests. Real tests for the code that parses the AI response: a broken response, and a valid-looking response with wrong values.
NICE TO HAVE, only after 1-6 work, in this order: live deployed link; abuse protection (per-IP rate limit, block the same email or phone entering twice); CSV export and a category filter in admin; Open Graph tags on the result page; poster-style design. Skip the Hindi toggle and Docker unless I say otherwise.

REQUIRED DOCUMENTS: README.md (run locally in under 10 minutes, env vars, decisions and why, what is unfinished, assumptions, roughly how many hours I spent); AI_USAGE.md (tools and models used and for which parts; 3-5 real prompts that mattered; at least 2 real times the AI got something wrong and how I caught it; which parts I wrote or rewrote by hand); AI_SESSIONS.json and an ai-logs/ folder (exported chats, numbered S1, S2, ...; redact API keys and passwords; do not tidy the logs); .env.example with no real keys. Public GitHub repo with commits made as I go (no squashing), and the session id in the message when a session produced most of a commit, like "feat: entry API [S2]". They check the FULL git history for secrets.
SCORING: core flow works end to end 25; code quality 20; AI integration (structured output, validation, failure handling, mock mode) 20; security and edge cases 15; UI and mobile 10; README, AI_USAGE.md, logs and honesty 10.
REVIEW CALL: a 45-minute screen-share where I explain choices, say where AI helped or led me wrong, and make a small change live. Code I cannot explain hurts more than a missing feature.
RULES FROM THEM: do it on my own (AI tools are fine, another person is not); the brand is fictional, no real logos; if something is unclear, make a sensible assumption and write it in the README.

=== MY DECISIONS ===
- Stack: one FastAPI app (Python 3.13) with server-rendered Jinja2 templates, SQLAlchemy (SQLite locally; DATABASE_URL env var so a hosted Postgres works if I deploy), Pydantic v2, httpx for the AI call, pytest. A little vanilla JavaScript for client-side validation only. Mobile-first plain CSS. No frontend framework.
- Windows laptop, VS Code. I know Python and FastAPI well and React moderately; I am a fresher.
- Keep it small and readable. No over-engineering, no extra dependencies without asking me.

=== DESIGN RULES TO FOLLOW ===
- Data model: internal id, a random public_id for URLs (for example secrets.token_urlsafe), name, city, contact (normalised) and contact type, story, consent plus timestamp, status (approved | rejected | pending_review), AI decision, reason, category, caption, AI error note, created and reviewed timestamps, admin override flag. A unique index on the normalised contact only if I build duplicate blocking.
- AI module: one function takes the story and returns a validated result. A Pydantic model enforces the enums, caption of 12 words or fewer, non-empty caption, and reason required when rejected. Any exception, timeout, rate limit or invalid result becomes pending_review. Log the error TYPE, never the story text. The mock provider is deterministic (for example spam words give a rejection, keywords pick the category, the caption comes from fixed rules).
- Prompt injection: treat the story as untrusted data; rely on schema validation, not on the prompt, for safety.
- Public pages: only approved entries are visible; everything else returns 404. Show the first name and the caption only, never email, phone or city.
- Admin: credentials from env vars, constant-time comparison, a signed session cookie, login attempt limiting, and CSRF protection for the override action.
- Server validation: lengths, contact format, consent must be true, trimmed inputs, escaped output (Jinja2 autoescape on). Never trust the client.
- Secrets: only in .env (gitignored); .env.example has placeholders; never print keys; check history before making the repo public.

=== HOW TO WORK WITH ME ===
1. START by asking me anything missing, then propose a short repo structure and a 4-session plan with time estimates. Wait for my OK.
2. Work in small steps. For each step: say what we are doing and why in two or three lines; show the code; tell me what to run to verify; wait for me to confirm it worked before moving on.
3. I WRITE BY HAND (you guide, you do not write): the AI response parser and its tests, and the server-side validation rules. For these, give me a spec and test cases, let me write the code, then review it and show me anything I missed.
4. Everything else you may draft, but explain it, and ask me to explain it back before we commit. If I cannot explain a part, simplify it.
5. Be sceptical of your own output. Tell me what you are unsure about, and what could be wrong, so I can test it. When you make a mistake, say so plainly. I will record real mistakes for AI_USAGE.md. Never claim something works without a command I can run.
6. At the end of each session give me: a commit message with the session id (for example "feat: AI parser [S2]"); a ready-to-paste AI_SESSIONS.json entry (id, tool, model, date, goal, log path, commits, files, kept, changed, rejected, mistakes_caught); and a reminder to export this chat to ai-logs/ and redact any secrets.
7. Keep a running list of "AI mistakes caught", "what I changed", and "what I rejected" so AI_USAGE.md is easy to write.
8. No extra features before items 1-6 work end to end. Tell me if I am drifting.
9. Near the end: help me run a clean-clone test (fresh folder, mock mode, setup under 10 minutes), a secrets scan of the full git history, a security checklist (direct API calls with bad input, XSS attempt, long inputs, guessing URLs, admin routes without login), and a rehearsal of the review call: ask me to explain each file and make 3 small live changes (for example add a new category, change the caption limit, add a status filter).

START by confirming you understand, then ask any questions you need before proposing the structure.
```

## Tonight (45-60 minutes, then sleep)

1. Open the new build chat, paste the prompt above, then paste the full assignment text.
2. Create the GitHub repo (public later, private for now), clone it, and make the first commit (a README skeleton and a `.gitignore` that covers `.env`).
3. Get a free API key from Groq or Gemini, put it in a local `.env` (never commit it), and test one request. If it works, you have the real path ready. If no free key works, mock mode alone is acceptable, but note it in the README.
4. Save the planning text from this chat into `ai-logs/S0-claude-planning.md`, with unrelated personal parts replaced by `[removed: unrelated]`.
5. Write down your assumptions as you go (for example "phone numbers: digits only, 10-15 digits").

Then stop and sleep. Wednesday's first block (7:10-8:40) starts the project skeleton.

## Three things to protect

- **Don't let the assistant write the parser and tests for you.** Those are the pieces they'll probe hardest. Write them yourself, and list them under `written_by_hand`.
- **Don't squash commits or edit the logs.** Messy is fine. They say dead ends tell them more than a clean log would.
- **Tell the truth in `AI_USAGE.md`.** List real mistakes the AI made, not made-up ones. They'll compare it to your logs.

After your first build session, paste me the session summary and anything confusing, and I'll help you check your design against the scoring table. Good luck.
